import React, { useEffect, useRef } from "react";

export default function AlertBanner({ alert }) {
  const audioCtxRef = useRef(null);

  useEffect(() => {
    if (!alert) return;
    try {
      const ctx = audioCtxRef.current || new (window.AudioContext || window.webkitAudioContext)();
      audioCtxRef.current = ctx;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "square";
      osc.frequency.value = 880;
      gain.gain.value = 0.05;
      osc.connect(gain).connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.18);
    } catch (e) {
      // Audio may be blocked until the user interacts with the page; that's fine.
    }
  }, [alert]);

  if (!alert) return null;

  return (
    <div className="alert-banner">
      ⚠ FAILURE RISK DETECTED — {alert.machine_id} — probability {(alert.probability * 100).toFixed(1)}%
      &nbsp;(threshold {(alert.alert_threshold * 100).toFixed(0)}%)
    </div>
  );
}
