"""
simulate_sensor.py
-------------------
Software stand-in for the ESP32 hardware. Streams realistic sensor
readings (with a slow degradation ramp toward failure) to the backend's
/get-data endpoint, so you can demo and test the full pipeline -
dashboard, alerts, charts - without any physical hardware.

Usage:
    python simulate_sensor.py --url http://localhost:5000/get-data \
                               --machine-id machine-1 --interval 2
"""

import argparse
import time
import random
import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:5000/get-data")
    parser.add_argument("--machine-id", default="machine-1")
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between readings")
    parser.add_argument("--cycles", type=int, default=0, help="0 = run forever, looping the ramp")
    args = parser.parse_args()

    cycle = 0
    ramp_len = 120  # readings per full healthy->failure->reset cycle

    while True:
        progress = (cycle % ramp_len) / ramp_len
        degradation = progress ** 2

        temperature = 65 + degradation * 35 + random.gauss(0, 1.2)
        vibration = 0.3 + degradation * 2.5 + random.gauss(0, 0.05)
        pressure = 100 - degradation * 20 + random.gauss(0, 1.5)

        payload = {
            "machine_id": args.machine_id,
            "temperature": round(temperature, 2),
            "vibration": round(vibration, 3),
            "pressure": round(pressure, 2),
        }

        try:
            resp = requests.post(args.url, json=payload, timeout=5)
            data = resp.json()
            print(f"cycle={cycle:4d}  T={payload['temperature']:6.2f}  "
                  f"Vib={payload['vibration']:.3f}  P={payload['pressure']:6.2f}  "
                  f"-> prob={data.get('probability')}  status={data.get('status')}")
        except Exception as e:
            print(f"Failed to send reading: {e}")

        cycle += 1
        if args.cycles and cycle >= args.cycles:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
