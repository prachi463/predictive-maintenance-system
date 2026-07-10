"""
db.py
-----
Data access layer. Uses MongoDB Atlas if MONGO_URI is set in the
environment (production mode). If it isn't set, falls back to a local
SQLite file automatically, so the whole system is runnable and demoable
with zero cloud setup, then becomes "real" the moment you add a
MongoDB Atlas connection string to .env.
"""

import os
import sqlite3
import json
from datetime import datetime, timezone

MONGO_URI = os.getenv("MONGO_URI", "").strip()
USE_MONGO = bool(MONGO_URI)

if USE_MONGO:
    from pymongo import MongoClient, DESCENDING

    _client = MongoClient(MONGO_URI)
    _db = _client[os.getenv("MONGO_DB_NAME", "predictive_maintenance")]
    _readings = _db["readings"]
    _readings.create_index([("machine_id", 1), ("timestamp", DESCENDING)])
else:
    _SQLITE_PATH = os.path.join(os.path.dirname(__file__), "local_data.db")
    _conn = sqlite3.connect(_SQLITE_PATH, check_same_thread=False)
    _conn.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            temperature REAL,
            vibration REAL,
            pressure REAL,
            prediction INTEGER,
            probability REAL
        )
    """)
    _conn.commit()


def insert_reading(machine_id, temperature, vibration, pressure, prediction, probability, timestamp=None):
    timestamp = timestamp or datetime.now(timezone.utc).isoformat()
    doc = {
        "machine_id": str(machine_id),
        "timestamp": timestamp,
        "temperature": float(temperature),
        "vibration": float(vibration),
        "pressure": float(pressure),
        "prediction": int(prediction),
        "probability": float(probability),
    }

    if USE_MONGO:
        _readings.insert_one(doc)
    else:
        _conn.execute(
            """INSERT INTO readings
               (machine_id, timestamp, temperature, vibration, pressure, prediction, probability)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (doc["machine_id"], doc["timestamp"], doc["temperature"], doc["vibration"],
             doc["pressure"], doc["prediction"], doc["probability"]),
        )
        _conn.commit()
    return doc


def get_recent(machine_id, limit=15):
    """Most recent `limit` readings for a machine, oldest first (for sequence building)."""
    if USE_MONGO:
        cursor = _readings.find({"machine_id": str(machine_id)}) \
            .sort("timestamp", DESCENDING).limit(limit)
        rows = list(cursor)[::-1]
        for r in rows:
            r["_id"] = str(r["_id"])
        return rows
    else:
        cur = _conn.execute(
            """SELECT machine_id, timestamp, temperature, vibration, pressure, prediction, probability
               FROM readings WHERE machine_id = ? ORDER BY timestamp DESC LIMIT ?""",
            (str(machine_id), limit),
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        return rows[::-1]


def get_history(machine_id, limit=200):
    if USE_MONGO:
        cursor = _readings.find({"machine_id": str(machine_id)}) \
            .sort("timestamp", DESCENDING).limit(limit)
        rows = list(cursor)[::-1]
        for r in rows:
            r["_id"] = str(r["_id"])
        return rows
    else:
        cur = _conn.execute(
            """SELECT machine_id, timestamp, temperature, vibration, pressure, prediction, probability
               FROM readings WHERE machine_id = ? ORDER BY timestamp DESC LIMIT ?""",
            (str(machine_id), limit),
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        return rows[::-1]


def list_machines():
    if USE_MONGO:
        return _readings.distinct("machine_id")
    else:
        cur = _conn.execute("SELECT DISTINCT machine_id FROM readings")
        return [row[0] for row in cur.fetchall()]


def backend_mode():
    return "mongodb_atlas" if USE_MONGO else "sqlite_local_fallback"
