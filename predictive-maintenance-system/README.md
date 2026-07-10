# UNIT-CTRL — AI-Powered Predictive Maintenance System

LSTM-based failure prediction, real IoT (ESP32) integration, MongoDB time-series
storage, and a SCADA-style real-time dashboard.

```
Sensors (ESP32) → Flask/Socket.IO API → MongoDB Atlas → LSTM inference
                                                 │
                                                 ▼
                                   React SCADA Dashboard (live charts, alerts)
```

## Project structure

```
predictive-maintenance-system/
├── model/              LSTM training pipeline
│   ├── generate_synthetic_data.py
│   ├── utils.py             (shared sequence/scaling logic — training & serving use this)
│   ├── train_lstm.py
│   └── requirements.txt
├── backend/             Flask + Socket.IO API
│   ├── app.py
│   ├── db.py               (MongoDB Atlas, auto-falls back to local SQLite)
│   ├── requirements.txt
│   └── .env.example
├── frontend/             React SCADA dashboard (Vite)
│   └── src/...
├── iot/                 ESP32 firmware + software simulator
│   ├── esp32_sensor_node.ino     (Arduino)
│   ├── esp32_micropython.py       (MicroPython alternative)
│   └── simulate_sensor.py          (no-hardware demo mode)
└── data/
    └── sensor_data.csv     (pre-generated 900-row synthetic sample, ready to train on)
```

## 1. Quick start (no hardware required, ~10 minutes)

### 1.1 Train the LSTM model

```bash
cd model
pip install -r requirements.txt
python generate_synthetic_data.py --machines 5 --cycles 400 --out ../data/sensor_data.csv
python train_lstm.py --data ../data/sensor_data.csv --epochs 30
```

This produces `lstm_model.h5`, `scaler.save`, `metrics.json`, and `training_history.png`
inside `model/`. The backend loads these automatically.

### 1.2 Run the backend

```bash
cd ../backend
pip install -r requirements.txt
cp .env.example .env      # leave MONGO_URI blank to use local SQLite instead
python app.py
```

The API is now live at `http://localhost:5000`. Check `http://localhost:5000/health`.

### 1.3 Feed it data (simulator, no ESP32 needed)

```bash
cd ../iot
pip install requests
python simulate_sensor.py --url http://localhost:5000/get-data --machine-id machine-1 --interval 2
```

This streams a realistic healthy → degrading → failure cycle so you can watch
the dashboard react in real time. Run it twice with different `--machine-id`
values to simulate multiple machines.

### 1.4 Run the dashboard

```bash
cd ../frontend
npm install
npm run dev
```

Open `http://localhost:5173`. You should see live gauges, sensor trend charts,
the failure-probability trend, and a flashing alert banner once probability
crosses the threshold (default 70%, adjustable from the sidebar).

## 2. Using real IoT hardware (ESP32)

1. Wire up: DHT22 (temperature) → GPIO 4, vibration sensor (e.g. SW-420) →
   GPIO 34, analog pressure sensor → GPIO 35.
2. Open `iot/esp32_sensor_node.ino` in Arduino IDE. Install libraries: `DHT
   sensor library`, `Adafruit Unified Sensor`, `ArduinoJson`.
3. Set `WIFI_SSID`, `WIFI_PASSWORD`, and `SERVER_URL` (point at your deployed
   backend's `/get-data` endpoint) at the top of the file.
4. Flash to the ESP32. Open Serial Monitor at 115200 baud to confirm readings
   are sending successfully.
5. Prefer MicroPython? Use `iot/esp32_micropython.py` instead — same wiring,
   flash with `ampy`/`Thonny`/`rshell`.

## 3. Using a real-world dataset (NASA C-MAPSS / Kaggle)

`train_lstm.py` expects a CSV with columns: `machine_id, timestamp, temperature,
vibration, pressure, label`. Real datasets like NASA's Turbofan Degradation
Simulation don't come in this exact shape, so:

1. Download the dataset (NASA C-MAPSS or a Kaggle predictive-maintenance set).
2. Map the closest available sensor channels to `temperature`, `vibration`,
   `pressure` (rename columns, or average correlated sensors).
3. Derive `label`: for C-MAPSS, compute Remaining Useful Life (RUL) per cycle
   (`max_cycle - current_cycle`) and set `label = 1` when `RUL <= 15` (or
   whatever danger window makes sense for your data).
4. Save as CSV and point `train_lstm.py --data your_file.csv` at it — no code
   changes needed downstream.

## 4. Production deployment

**Database — MongoDB Atlas (free tier is enough for this):**
1. Create a free cluster at cloud.mongodb.com.
2. Add a database user + allow network access from anywhere (0.0.0.0/0) or
   your specific deployment IPs.
3. Copy the connection string into `backend/.env` as `MONGO_URI`.

**Backend — Render or Railway:**
1. Push this repo to GitHub.
2. On Render: New → Web Service → point at `backend/`, build command
   `pip install -r requirements.txt`, start command `python app.py`.
3. Add environment variables (`MONGO_URI`, `MONGO_DB_NAME`, `ALERT_THRESHOLD`)
   in the Render/Railway dashboard.
4. Copy the resulting HTTPS URL — this is your backend's public API.

**Frontend — Vercel or Netlify:**
1. Set the environment variable `VITE_API_URL` to your deployed backend URL.
2. Import the repo in Vercel, set root directory to `frontend/`, framework
   preset "Vite". Deploy.

**ESP32:**
Update `SERVER_URL` in the firmware to your deployed backend's `/get-data`
endpoint (must be HTTPS if using Render/Railway's default domain).

## 5. API reference

| Method | Endpoint            | Purpose                                            |
|--------|----------------------|-----------------------------------------------------|
| POST   | `/get-data`           | Ingest one IoT reading, run LSTM, store, broadcast |
| GET    | `/history`             | Historical time-series for a machine (for charts) |
| POST   | `/predict`              | Raw sequence → prediction (for testing tools)     |
| GET    | `/machines`              | List of machine IDs seen so far                  |
| GET    | `/metrics`                | Model accuracy/precision/recall/AUC              |
| GET    | `/report/<machine_id>`     | Download CSV report                            |
| GET/POST | `/threshold`               | Read/update the alert probability threshold   |
| GET    | `/health`                    | Liveness + which storage backend is active   |

Real-time: the backend also emits Socket.IO events `sensor_update` (every
reading) and `failure_alert` (only when prediction = 1), which the dashboard
subscribes to for instant updates without polling.

## 6. Advanced features included

- WebSocket real-time streaming (Socket.IO) alongside REST polling fallback
- CSV report download per machine
- Model accuracy/precision/recall/AUC surfaced in the dashboard header
- Adjustable alert threshold from the UI (persisted to the backend)
- Multi-machine monitoring (sidebar machine list with live status badges)
- Graceful fallback: API works even before you've trained a model (rule-based
  predictor) and even without MongoDB (local SQLite)

## 7. Notes for your resume / report

- **Problem framing**: time-series failure prediction from multivariate
  sensor telemetry using a windowed LSTM classifier.
- **Data pipeline**: MinMax scaling + fixed-length sequence windows (15
  timesteps), identical logic shared between training and serving via
  `model/utils.py` to avoid train/serve skew.
- **Model**: 2-layer LSTM (64→32 units) with dropout, binary cross-entropy,
  evaluated on accuracy/precision/recall/AUC (see `model/metrics.json` after
  training).
- **Systems integration**: ESP32 → HTTP → Flask/Socket.IO → MongoDB Atlas →
  React dashboard, end-to-end real-time path from sensor to alert.
