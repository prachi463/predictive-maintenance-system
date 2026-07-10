"""
generate_synthetic_data.py
--------------------------
Generates a realistic synthetic time-series dataset for machine sensor
readings (temperature, vibration, pressure) with an injected degradation
pattern that leads to failure, so the LSTM has a real signal to learn.

Usage:
    python generate_synthetic_data.py --machines 5 --cycles 400 --out ../data/sensor_data.csv

This mimics the structure of the NASA C-MAPSS / Kaggle predictive
maintenance datasets: one row per (machine_id, cycle) with sensor columns
and a remaining-useful-life-derived failure label, so you can swap this
file out for a real dataset with zero code changes downstream.
"""

import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def simulate_machine(machine_id: int, cycles: int, start_time: datetime, rng: np.random.Generator):
    """Simulate one machine's lifetime: healthy -> degrading -> failure."""
    # Failure point is random within the later part of the run, so every
    # machine has a different remaining-useful-life curve.
    failure_cycle = rng.integers(int(cycles * 0.6), cycles)

    temps, vibs, press, labels, probs, timestamps = [], [], [], [], [], []

    base_temp = rng.uniform(60, 70)
    base_vib = rng.uniform(0.2, 0.4)
    base_pressure = rng.uniform(95, 105)

    for cycle in range(cycles):
        # Degradation factor ramps up as we approach the failure cycle.
        distance_to_failure = failure_cycle - cycle
        degradation = max(0.0, 1 - (distance_to_failure / failure_cycle))
        degradation = degradation ** 2  # nonlinear ramp, more realistic

        temp = base_temp + degradation * 35 + rng.normal(0, 1.2)
        vib = base_vib + degradation * 2.5 + rng.normal(0, 0.05)
        pressure = base_pressure - degradation * 20 + rng.normal(0, 1.5)

        # Label: 1 if within the "danger window" before failure
        danger_window = 15
        label = 1 if distance_to_failure <= danger_window else 0
        # Probability-ish target used only for reference/eval, not fed to model
        prob = float(np.clip(degradation, 0, 1))

        temps.append(round(temp, 2))
        vibs.append(round(vib, 3))
        press.append(round(pressure, 2))
        labels.append(label)
        probs.append(round(prob, 3))
        timestamps.append(start_time + timedelta(minutes=5 * cycle))

    return pd.DataFrame({
        "machine_id": machine_id,
        "timestamp": timestamps,
        "cycle": np.arange(cycles),
        "temperature": temps,
        "vibration": vibs,
        "pressure": press,
        "failure_probability_true": probs,
        "label": labels,
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machines", type=int, default=5, help="Number of machines to simulate")
    parser.add_argument("--cycles", type=int, default=400, help="Cycles (time steps) per machine")
    parser.add_argument("--out", type=str, default="../data/sensor_data.csv", help="Output CSV path")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    start = datetime.now()

    frames = [
        simulate_machine(mid, args.cycles, start, rng)
        for mid in range(1, args.machines + 1)
    ]
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows across {args.machines} machines -> {args.out}")
    print(df.head())


if __name__ == "__main__":
    main()
