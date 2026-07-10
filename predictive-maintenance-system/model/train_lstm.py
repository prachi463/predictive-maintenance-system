"""
train_lstm.py
-------------
Trains an LSTM binary classifier that predicts imminent-failure risk from
a rolling window of (temperature, vibration, pressure) readings.

Works with:
  1. The synthetic dataset from generate_synthetic_data.py, OR
  2. A real dataset (NASA C-MAPSS, Kaggle Predictive Maintenance) as long
     as it's reshaped into columns: machine_id, timestamp, temperature,
     vibration, pressure, label  (see README "Using a real dataset").

Outputs (saved into model/ folder):
  - lstm_model.h5        Trained Keras model
  - scaler.save          Fitted MinMaxScaler (joblib)
  - training_history.png Loss/accuracy curves
  - metrics.json         Final accuracy/precision/recall/AUC for the dashboard
"""

import argparse
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score

import tensorflow as tf
from tensorflow.keras import layers, models, callbacks

from utils import build_sequences, FEATURE_COLUMNS, SEQUENCE_LENGTH


def load_data(path):
    df = pd.read_csv(path, parse_dates=["timestamp"])
    required = {"machine_id", "timestamp", "label"} | set(FEATURE_COLUMNS)
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")
    return df.sort_values(["machine_id", "timestamp"])


def build_model(seq_len, num_features):
    model = models.Sequential([
        layers.Input(shape=(seq_len, num_features)),
        layers.LSTM(64, return_sequences=True),
        layers.Dropout(0.2),
        layers.LSTM(32),
        layers.Dropout(0.2),
        layers.Dense(16, activation="relu"),
        layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="binary_crossentropy",
        metrics=["accuracy", tf.keras.metrics.AUC(name="auc")],
    )
    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default="../data/sensor_data.csv")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--seq_len", type=int, default=SEQUENCE_LENGTH)
    args = parser.parse_args()

    print("Loading data...")
    df = load_data(args.data)

    print("Scaling features...")
    scaler = MinMaxScaler()
    df[FEATURE_COLUMNS] = scaler.fit_transform(df[FEATURE_COLUMNS])
    joblib.dump(scaler, "scaler.save")

    print("Building sequences...")
    X, y = build_sequences(df, seq_len=args.seq_len)
    print(f"X shape: {X.shape}, y shape: {y.shape}, positive rate: {y.mean():.3f}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = build_model(args.seq_len, len(FEATURE_COLUMNS))
    model.summary()

    early_stop = callbacks.EarlyStopping(
        monitor="val_loss", patience=5, restore_best_weights=True
    )

    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=args.epochs,
        batch_size=args.batch_size,
        callbacks=[early_stop],
        verbose=2,
    )

    print("Evaluating...")
    y_pred_prob = model.predict(X_test).ravel()
    y_pred = (y_pred_prob > 0.5).astype(int)

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "auc": float(roc_auc_score(y_test, y_pred_prob)),
        "sequence_length": args.seq_len,
        "features": FEATURE_COLUMNS,
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
    }
    print("Final metrics:", json.dumps(metrics, indent=2))

    with open("metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    model.save("lstm_model.h5")
    print("Saved model -> lstm_model.h5, scaler -> scaler.save, metrics -> metrics.json")

    # Save training curves for the dashboard / report
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        axes[0].plot(history.history["loss"], label="train_loss")
        axes[0].plot(history.history["val_loss"], label="val_loss")
        axes[0].set_title("Loss")
        axes[0].legend()

        axes[1].plot(history.history["accuracy"], label="train_acc")
        axes[1].plot(history.history["val_accuracy"], label="val_acc")
        axes[1].set_title("Accuracy")
        axes[1].legend()

        plt.tight_layout()
        plt.savefig("training_history.png", dpi=150)
        print("Saved training_history.png")
    except ImportError:
        print("matplotlib not installed, skipping training curve plot.")


if __name__ == "__main__":
    main()
