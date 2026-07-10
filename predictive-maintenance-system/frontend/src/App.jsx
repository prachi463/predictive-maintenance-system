import React, { useEffect, useState, useCallback } from "react";
import Sidebar from "./components/Sidebar.jsx";
import GaugeCard from "./components/GaugeCard.jsx";
import AlertBanner from "./components/AlertBanner.jsx";
import ChartsPanel from "./components/ChartsPanel.jsx";
import { useSensorSocket } from "./useSensorSocket.js";
import { getMachines, getHistory, getThreshold, setThreshold as pushThreshold, getMetrics } from "./api.js";

const POLL_MS = 4000;

export default function App() {
  const [machines, setMachines] = useState([]);
  const [selected, setSelected] = useState(null);
  const [history, setHistory] = useState([]);
  const [machineStatus, setMachineStatus] = useState({});
  const [threshold, setThresholdState] = useState(0.7);
  const [metrics, setMetrics] = useState(null);

  const { connected, lastReading, lastAlert } = useSensorSocket();

  // Initial load: machine list + threshold + model metrics
  useEffect(() => {
    getMachines().then((d) => {
      setMachines(d.machines || []);
      if (!selected && d.machines?.length) setSelected(d.machines[0]);
    }).catch(() => {});
    getThreshold().then((d) => setThresholdState(d.alert_threshold)).catch(() => {});
    getMetrics().then(setMetrics).catch(() => {});
  }, []);

  const refreshHistory = useCallback(() => {
    if (!selected) return;
    getHistory(selected, 200).then((d) => setHistory(d.data || [])).catch(() => {});
  }, [selected]);

  // Refresh history when machine changes, and poll as a fallback to websockets
  useEffect(() => {
    refreshHistory();
    const id = setInterval(refreshHistory, POLL_MS);
    return () => clearInterval(id);
  }, [refreshHistory]);

  // React to live websocket pushes
  useEffect(() => {
    if (!lastReading) return;
    setMachineStatus((prev) => ({ ...prev, [lastReading.machine_id]: lastReading.status }));
    setMachines((prev) => (prev.includes(lastReading.machine_id) ? prev : [...prev, lastReading.machine_id]));
    if (lastReading.machine_id === selected) {
      setHistory((prev) => [...prev.slice(-499), lastReading]);
    }
  }, [lastReading, selected]);

  const latest = history[history.length - 1];

  const handleThresholdChange = (val) => {
    setThresholdState(val);
    pushThreshold(val).catch(() => {});
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">PM</div>
          <div>
            <div className="brand-title">Unit-Ctrl // Predictive Maintenance</div>
            <div className="brand-subtitle">LSTM inference · MongoDB time-series · ESP32 telemetry</div>
          </div>
        </div>
        <div className="conn-pill">
          <span className={`dot ${connected ? "online" : ""}`} />
          {connected ? "LIVE STREAM CONNECTED" : "OFFLINE — POLLING"}
        </div>
      </header>

      <div className="main-grid">
        <Sidebar
          machines={machines}
          selected={selected}
          onSelect={setSelected}
          machineStatus={machineStatus}
          threshold={threshold}
          onThresholdChange={handleThresholdChange}
        />

        <main>
          <AlertBanner alert={lastAlert && lastAlert.machine_id === selected ? lastAlert : null} />

          <div className="status-strip">
            <span className="status-chip">
              MACHINE <b>{selected || "—"}</b>
            </span>
            <span className="status-chip">
              STATUS <b style={{ color: latest?.status === "RISK" || latest?.prediction === 1 ? "var(--accent-red)" : "var(--accent-cyan)" }}>
                {latest ? (latest.prediction === 1 ? "RISK" : "NORMAL") : "—"}
              </b>
            </span>
            <span className="status-chip">
              LAST UPDATE <b className="mono">{latest ? new Date(latest.timestamp).toLocaleString() : "—"}</b>
            </span>
            {metrics && (
              <span className="status-chip">
                MODEL ACCURACY <b className="mono">{(metrics.accuracy * 100).toFixed(1)}%</b>
              </span>
            )}
          </div>

          <div className="gauge-row">
            <GaugeCard label="Temperature" value={latest?.temperature} unit="°C" warnAt={85} dangerAt={95} />
            <GaugeCard label="Vibration" value={latest?.vibration} unit="g" decimals={2} warnAt={1.8} dangerAt={2.4} />
            <GaugeCard label="Pressure" value={latest?.pressure} unit="kPa" decimals={1} />
            <GaugeCard
              label="Failure Probability"
              value={latest ? latest.probability * 100 : null}
              unit="%"
              warnAt={threshold * 100 * 0.7}
              dangerAt={threshold * 100}
            />
          </div>

          <ChartsPanel history={history} />
        </main>
      </div>

      <div className="footer-note">
        UNIT-CTRL DASHBOARD · Prachi Verma · AI/ML Predictive Maintenance System
      </div>
    </div>
  );
}
