import React from "react";
import { reportUrl } from "../api.js";

export default function Sidebar({
  machines,
  selected,
  onSelect,
  machineStatus,
  threshold,
  onThresholdChange,
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="panel">
        <p className="panel-title">Machines <span className="mono">{machines.length}</span></p>
        <ul className="machine-list">
          {machines.length === 0 && (
            <li className="mono" style={{ color: "var(--text-dim)", fontSize: 12 }}>
              No machines yet — send a reading via the simulator or ESP32.
            </li>
          )}
          {machines.map((m) => {
            const status = machineStatus[m] || "NORMAL";
            return (
              <li
                key={m}
                className={`machine-item ${selected === m ? "active" : ""}`}
                onClick={() => onSelect(m)}
              >
                <span>{m}</span>
                <span className={`badge ${status === "RISK" ? "risk" : "normal"}`}>
                  {status}
                </span>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="panel">
        <p className="panel-title">Alert Threshold</p>
        <div className="threshold-box">
          <div className="threshold-value mono">{Math.round(threshold * 100)}%</div>
          <input
            type="range"
            min="0.1"
            max="0.95"
            step="0.05"
            value={threshold}
            onChange={(e) => onThresholdChange(parseFloat(e.target.value))}
          />
        </div>
        {selected && (
          <a href={reportUrl(selected)} target="_blank" rel="noreferrer">
            <button className="btn">Download CSV Report</button>
          </a>
        )}
      </div>
    </div>
  );
}
