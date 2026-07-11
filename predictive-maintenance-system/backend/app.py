"""
app.py
------
Flask backend for the Predictive Maintenance System.

Endpoints:
  POST /get-data      Ingest one IoT reading -> store -> run LSTM -> return prediction
  GET  /history        Historical time-series for a machine (for charts)
  POST /predict         Raw sequence -> prediction (for testing/tools)
  GET  /machines         List of machine IDs seen so far
  GET  /metrics          Model accuracy/precision/recall/AUC (from training)
  GET  /report/<machine_id>  Download CSV report of a machine's history
  GET  /health            Liveness check

Real-time streaming: Socket.IO broadcasts every new reading on the
"sensor_update" event, so the dashboard can update without polling.

Run:
  pip install -r requirements.txt
  python app.py
"""

import os
import io
import csv
import sys
import json
from datetime import datetime, timezone

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "model"))
from utils import build_single_sequence, FEATURE_COLUMNS, SEQUENCE_LENGTH  # noqa: E402
import db  # noqa: E402

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "model")
MODEL_PATH = os.path.join(MODEL_DIR, "lstm_model.h5")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.save")
METRICS_PATH = os.path.join(MODEL_DIR, "metrics.json")

ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", "0.7"))

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------------------------------------------------------------
# Model loading (lazy + graceful fallback so the API works even before
# you've run model/train_lstm.py for the first time)
# ---------------------------------------------------------------------
_model = None
_scaler = None
_model_loaded = False


def load_model_assets():
    global _model, _scaler, _model_loaded
    if _model_loaded:
        return
    try:
        import tensorflow as tf
        import joblib
        _model = tf.keras.models.load_model(MODEL_PATH)
        _scaler = joblib.load(SCALER_PATH)
        print("LSTM model + scaler loaded successfully.")
    except Exception as e:
        print(f"[WARN] Could not load trained model ({e}). "
              f"Falling back to a rule-based predictor until you run "
              f"`python model/train_lstm.py`.")
        _model = None
        _scaler = None
    _model_loaded = True


def rule_based_probability(temperature, vibration, pressure):
    """Simple heuristic fallback used only when no trained model exists yet."""
    score = 0.0
    score += max(0, (temperature - 75) / 40)
    score += max(0, (vibration - 1.0) / 3.0)
    score += max(0, (95 - pressure) / 40)
    return float(min(1.0, score / 3))


def predict_from_sequence(seq_records):
    """seq_records: list of dicts with temperature/vibration/pressure, oldest first."""
    load_model_assets()

    if _model is not None and _scaler is not None:
        import numpy as np
        raw = build_single_sequence(seq_records, seq_len=SEQUENCE_LENGTH)
        flat = raw.reshape(-1, len(FEATURE_COLUMNS))
        scaled = _scaler.transform(flat).reshape(raw.shape)
        prob = float(_model.predict(scaled, verbose=0)[0][0])
    else:
        last = seq_records[-1]
        prob = rule_based_probability(last["temperature"], last["vibration"], last["pressure"])

    prediction = int(prob > ALERT_THRESHOLD)
    return prediction, round(prob, 4)


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "storage_backend": db.backend_mode(),
        "model_loaded": _model is not None,
        "alert_threshold": ALERT_THRESHOLD,
    })


@app.route("/get-data", methods=["POST"])
def get_data():
    """
    Called by the ESP32 (or any IoT client / simulator) with a JSON body:
    {
      "machine_id": "machine-1",
      "temperature": 72.5,
      "vibration": 0.42,
      "pressure": 101.2,
      "timestamp": "2026-07-10T12:00:00Z"   (optional, server time used if absent)
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    required = {"machine_id", "temperature", "vibration", "pressure"}
    missing = required - set(data.keys())
    if missing:
        return jsonify({"error": f"Missing fields: {sorted(missing)}"}), 400

    machine_id = str(data["machine_id"])
    timestamp = data.get("timestamp") or datetime.now(timezone.utc).isoformat()

    # Build sequence context: prior readings + this new one
    history = db.get_recent(machine_id, limit=SEQUENCE_LENGTH - 1)
    seq_records = history + [{
        "temperature": data["temperature"],
        "vibration": data["vibration"],
        "pressure": data["pressure"],
    }]

    prediction, probability = predict_from_sequence(seq_records)

    doc = db.insert_reading(
        machine_id=machine_id,
        temperature=data["temperature"],
        vibration=data["vibration"],
        pressure=data["pressure"],
        prediction=prediction,
        probability=probability,
        timestamp=timestamp,
    )

    status = "RISK" if prediction == 1 else "NORMAL"
    payload = {**doc, "status": status, "alert_threshold": ALERT_THRESHOLD}

    # Push to any connected dashboards in real time
    socketio.emit("sensor_update", payload)
    if prediction == 1:
        socketio.emit("failure_alert", payload)

    return jsonify(payload), 201


@app.route("/history", methods=["GET"])
def history():
    machine_id = request.args.get("machine_id", "machine-1")
    limit = int(request.args.get("limit", 200))
    rows = db.get_history(machine_id, limit=limit)
    return jsonify({"machine_id": machine_id, "count": len(rows), "data": rows})


@app.route("/machines", methods=["GET"])
def machines():
    return jsonify({"machines": db.list_machines()})


@app.route("/predict", methods=["POST"])
def predict():
    """
    Accepts a raw sequence for testing/tools:
    { "machine_id": "machine-1", "sequence": [ {temperature, vibration, pressure}, ... ] }
    If "sequence" is omitted, uses the machine's stored history instead.
    """
    data = request.get_json(force=True, silent=True) or {}
    machine_id = data.get("machine_id", "machine-1")

    seq_records = data.get("sequence")
    if not seq_records:
        seq_records = db.get_recent(machine_id, limit=SEQUENCE_LENGTH)
        if not seq_records:
            return jsonify({"error": "No sequence provided and no stored history for this machine."}), 400

    prediction, probability = predict_from_sequence(seq_records)
    return jsonify({
        "machine_id": machine_id,
        "prediction": prediction,
        "probability": probability,
        "status": "RISK" if prediction == 1 else "NORMAL",
    })


@app.route("/metrics", methods=["GET"])
def metrics():
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH) as f:
            return jsonify(json.load(f))
    return jsonify({"error": "No metrics.json found yet. Train the model first (model/train_lstm.py)."}), 404


@app.route("/report/<machine_id>", methods=["GET"])
def report(machine_id):
    rows = db.get_history(machine_id, limit=100000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["machine_id", "timestamp", "temperature", "vibration", "pressure", "prediction", "probability"])
    for r in rows:
        writer.writerow([r.get("machine_id"), r.get("timestamp"), r.get("temperature"),
                          r.get("vibration"), r.get("pressure"), r.get("prediction"), r.get("probability")])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={machine_id}_report.csv"},
    )


@app.route("/threshold", methods=["GET", "POST"])
def threshold():
    global ALERT_THRESHOLD
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        new_threshold = data.get("threshold")
        if new_threshold is None or not (0 < float(new_threshold) < 1):
            return jsonify({"error": "threshold must be a number between 0 and 1"}), 400
        ALERT_THRESHOLD = float(new_threshold)
    return jsonify({"alert_threshold": ALERT_THRESHOLD})


@socketio.on("connect")
def on_connect():
    print("Dashboard client connected via WebSocket.")


if __name__ == "__main__":
    load_model_assets()
    port = int(os.getenv("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
