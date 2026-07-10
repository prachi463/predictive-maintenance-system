import { useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";
import { API_BASE } from "./api.js";

/**
 * Subscribes to the backend's Socket.IO stream and returns the latest
 * live reading + a rolling connection status, so the dashboard updates
 * in real time instead of polling.
 */
export function useSensorSocket() {
  const [connected, setConnected] = useState(false);
  const [lastReading, setLastReading] = useState(null);
  const [lastAlert, setLastAlert] = useState(null);
  const socketRef = useRef(null);

  useEffect(() => {
    const socket = io(API_BASE, { transports: ["websocket", "polling"] });
    socketRef.current = socket;

    socket.on("connect", () => setConnected(true));
    socket.on("disconnect", () => setConnected(false));
    socket.on("sensor_update", (payload) => setLastReading(payload));
    socket.on("failure_alert", (payload) => setLastAlert(payload));

    return () => socket.disconnect();
  }, []);

  return { connected, lastReading, lastAlert };
}
