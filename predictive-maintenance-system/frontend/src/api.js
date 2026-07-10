import axios from "axios";

// Point this at your backend. In dev it's localhost:5000; after deploying
// the backend (Render/Railway) replace with the live URL, or set it via
// a Vite env var: VITE_API_URL=https://your-backend.onrender.com
export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";

const client = axios.create({ baseURL: API_BASE, timeout: 8000 });

export const getHealth = () => client.get("/health").then((r) => r.data);
export const getMachines = () => client.get("/machines").then((r) => r.data);
export const getHistory = (machineId, limit = 200) =>
  client.get("/history", { params: { machine_id: machineId, limit } }).then((r) => r.data);
export const getMetrics = () => client.get("/metrics").then((r) => r.data);
export const setThreshold = (threshold) =>
  client.post("/threshold", { threshold }).then((r) => r.data);
export const getThreshold = () => client.get("/threshold").then((r) => r.data);
export const reportUrl = (machineId) => `${API_BASE}/report/${machineId}`;
