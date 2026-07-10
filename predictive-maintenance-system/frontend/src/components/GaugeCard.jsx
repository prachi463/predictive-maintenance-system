import React from "react";

export default function GaugeCard({ label, value, unit, warnAt, dangerAt, decimals = 1 }) {
  let cls = "gauge-value";
  if (value != null && dangerAt != null && value >= dangerAt) cls += " danger";
  else if (value != null && warnAt != null && value >= warnAt) cls += " warn";

  return (
    <div className="panel gauge-card">
      <div className="gauge-label">{label}</div>
      <div className={cls}>
        {value != null ? value.toFixed(decimals) : "--"}
        <span className="gauge-unit">{unit}</span>
      </div>
    </div>
  );
}
