"""
utils.py
--------
Shared preprocessing helpers used by BOTH training (train_lstm.py) and the
backend inference API, so the exact same sequence-building logic is applied
at train time and at serve time (a common source of bugs otherwise).
"""

import numpy as np

FEATURE_COLUMNS = ["temperature", "vibration", "pressure"]
SEQUENCE_LENGTH = 15  # number of past readings the LSTM looks at


def build_sequences(df, seq_len=SEQUENCE_LENGTH, group_col="machine_id",
                     feature_cols=FEATURE_COLUMNS, label_col="label"):
    """
    Turn a flat per-cycle dataframe into (X, y) sequence arrays.

    X shape: (num_sequences, seq_len, num_features)
    y shape: (num_sequences,)  -- label of the LAST time step in the window
    """
    X, y = [], []
    if group_col in df.columns:
        groups = [g for _, g in df.groupby(group_col)]
    else:
        groups = [df]

    for g in groups:
        g = g.reset_index(drop=True)
        values = g[feature_cols].values
        labels = g[label_col].values if label_col in g.columns else None

        for i in range(len(g) - seq_len):
            window = values[i:i + seq_len]
            X.append(window)
            if labels is not None:
                y.append(labels[i + seq_len])

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.float32) if len(y) else None
    return X, y


def build_single_sequence(records, seq_len=SEQUENCE_LENGTH, feature_cols=FEATURE_COLUMNS):
    """
    Build one inference-ready sequence from the most recent `seq_len`
    sensor readings (a list of dicts with temperature/vibration/pressure).
    Pads with the earliest reading if fewer than seq_len are available yet.
    """
    if len(records) == 0:
        raise ValueError("No records provided to build a sequence from.")

    values = [[r[c] for c in feature_cols] for r in records[-seq_len:]]
    while len(values) < seq_len:
        values.insert(0, values[0])  # pad by repeating oldest reading

    return np.array([values], dtype=np.float32)  # shape (1, seq_len, num_features)
