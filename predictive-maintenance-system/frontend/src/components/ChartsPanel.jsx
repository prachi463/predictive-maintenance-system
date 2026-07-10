import React, { useMemo } from "react";
import { Line } from "react-chartjs-2";
import "../chartSetup.js";
import { darkChartOptions } from "../chartSetup.js";

const SEQ_LEN = 15;

function toLabels(rows) {
  return rows.map((r) => {
    const d = new Date(r.timestamp);
    return isNaN(d) ? r.timestamp : d.toLocaleTimeString();
  });
}

export default function ChartsPanel({ history }) {
  const labels = useMemo(() => toLabels(history), [history]);
  const sequenceSlice = history.slice(-SEQ_LEN);
  const sequenceLabels = toLabels(sequenceSlice);

  const sensorData = {
    labels,
    datasets: [
      {
        label: "Temperature (°C)",
        data: history.map((r) => r.temperature),
        borderColor: "#ff4d4f",
        backgroundColor: "rgba(255,77,79,0.08)",
        pointRadius: 0,
        borderWidth: 1.5,
        tension: 0.25,
      },
      {
        label: "Vibration (g)",
        data: history.map((r) => r.vibration),
        borderColor: "#4c8dff",
        backgroundColor: "rgba(76,141,255,0.08)",
        pointRadius: 0,
        borderWidth: 1.5,
        tension: 0.25,
        yAxisID: "y",
      },
      {
        label: "Pressure (kPa)",
        data: history.map((r) => r.pressure),
        borderColor: "#22d3c8",
        backgroundColor: "rgba(34,211,200,0.08)",
        pointRadius: 0,
        borderWidth: 1.5,
        tension: 0.25,
      },
    ],
  };

  const probabilityData = {
    labels,
    datasets: [
      {
        label: "Failure probability",
        data: history.map((r) => r.probability),
        borderColor: "#ffab2e",
        backgroundColor: "rgba(255,171,46,0.15)",
        pointRadius: 0,
        borderWidth: 1.5,
        fill: true,
        tension: 0.25,
      },
    ],
  };

  const sequenceData = {
    labels: sequenceLabels,
    datasets: [
      {
        label: "Temperature (scaled window)",
        data: sequenceSlice.map((r) => r.temperature),
        borderColor: "#ff4d4f",
        borderWidth: 1.5,
        pointRadius: 2,
        pointBackgroundColor: "#ff4d4f",
      },
      {
        label: "Vibration (scaled window)",
        data: sequenceSlice.map((r) => r.vibration * 10), // scaled up visually to share the axis
        borderColor: "#4c8dff",
        borderWidth: 1.5,
        pointRadius: 2,
        pointBackgroundColor: "#4c8dff",
      },
    ],
  };

  return (
    <div className="charts-grid">
      <div className="panel chart-panel">
        <p className="panel-title">Sensor Trends</p>
        <Line data={sensorData} options={darkChartOptions()} />
      </div>

      <div className="panel chart-panel">
        <p className="panel-title">Failure Probability Trend</p>
        <Line data={probabilityData} options={darkChartOptions("Probability")} />
      </div>

      <div className="panel chart-panel" style={{ gridColumn: "1 / -1" }}>
        <p className="panel-title">
          LSTM Input Window <span className="mono" style={{ color: "var(--text-dim)" }}>last {SEQ_LEN} readings</span>
        </p>
        <Line data={sequenceData} options={darkChartOptions()} />
      </div>
    </div>
  );
}
