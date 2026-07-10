"""
esp32_micropython.py
---------------------
MicroPython alternative to esp32_sensor_node.ino, for ESP32 boards
flashed with MicroPython firmware instead of Arduino.

Flash with: ampy / Thonny / rshell, then reset the board.

Requires: dht.py (built into MicroPython's ESP32 firmware), urequests
(install via `upip.install('micropython-urequests')` or copy urequests.py
onto the board manually).
"""

import machine
import dht
import time
import ujson
import network
import urequests

# ---------------- CONFIG ----------------
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
SERVER_URL = "http://192.168.1.100:5000/get-data"
MACHINE_ID = "machine-1"
INTERVAL_S = 5

DHT_PIN = 4
VIBRATION_PIN = 34
PRESSURE_PIN = 35
# -----------------------------------------

sensor = dht.DHT22(machine.Pin(DHT_PIN))
vibration_adc = machine.ADC(machine.Pin(VIBRATION_PIN))
vibration_adc.atten(machine.ADC.ATTN_11DB)
pressure_adc = machine.ADC(machine.Pin(PRESSURE_PIN))
pressure_adc.atten(machine.ADC.ATTN_11DB)


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("Connected:", wlan.ifconfig())


def read_vibration():
    raw = vibration_adc.read()  # 0-4095
    return round((raw / 4095.0) * 5.0, 3)


def read_pressure():
    raw = pressure_adc.read()
    voltage = (raw / 4095.0) * 3.3
    return round(80.0 + (voltage / 3.3) * 40.0, 2)


def send_reading(temperature, vibration, pressure):
    payload = {
        "machine_id": MACHINE_ID,
        "temperature": temperature,
        "vibration": vibration,
        "pressure": pressure,
    }
    try:
        resp = urequests.post(SERVER_URL, data=ujson.dumps(payload),
                               headers={"Content-Type": "application/json"})
        print("POST ->", resp.status_code, resp.text)
        resp.close()
    except Exception as e:
        print("Send failed:", e)


def main():
    connect_wifi()
    while True:
        try:
            sensor.measure()
            temperature = sensor.temperature()
            vibration = read_vibration()
            pressure = read_pressure()
            print("T={} Vib={} P={}".format(temperature, vibration, pressure))
            send_reading(temperature, vibration, pressure)
        except Exception as e:
            print("Reading failed:", e)
        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    main()
