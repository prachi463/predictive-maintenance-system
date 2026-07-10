/*
  esp32_sensor_node.ino
  ---------------------
  ESP32 firmware for the Predictive Maintenance System.

  Reads:
    - Temperature: DHT22 (or DHT11) on GPIO 4
    - Vibration:   SW-420 digital vibration sensor on GPIO 34 (analog-capable pin)
    - Pressure:    Analog pressure sensor (e.g. MPX4115) on GPIO 35

  Sends a JSON POST to the backend's /get-data endpoint every INTERVAL_MS.

  Libraries needed (install via Arduino Library Manager):
    - DHT sensor library (Adafruit)
    - Adafruit Unified Sensor
    - ArduinoJson
    (WiFi.h and HTTPClient.h ship with the ESP32 board package)
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ---------------- CONFIG ----------------
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Point this at your deployed backend, e.g. https://your-app.onrender.com/get-data
const char* SERVER_URL = "http://192.168.1.100:5000/get-data";

const char* MACHINE_ID = "machine-1";
const unsigned long INTERVAL_MS = 5000; // send every 5 seconds

#define DHTPIN 4
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE);

#define VIBRATION_PIN 34
#define PRESSURE_PIN  35
// -----------------------------------------

unsigned long lastSend = 0;

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected. IP address: " + WiFi.localIP().toString());
}

float readVibration() {
  // SW-420 outputs an analog-ish signal on ESP32's ADC pin (0-4095).
  // Normalize to a 0-5 "g-equivalent" style scale used by the ML model.
  int raw = analogRead(VIBRATION_PIN);
  return (raw / 4095.0) * 5.0;
}

float readPressure() {
  // Example for an analog pressure transducer, adjust the formula to
  // your specific sensor's datasheet (this maps 0-3.3V to 80-120 kPa).
  int raw = analogRead(PRESSURE_PIN);
  float voltage = (raw / 4095.0) * 3.3;
  return 80.0 + (voltage / 3.3) * 40.0;
}

void sendReading(float temperature, float vibration, float pressure) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected, skipping send.");
    return;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<256> doc;
  doc["machine_id"] = MACHINE_ID;
  doc["temperature"] = temperature;
  doc["vibration"] = vibration;
  doc["pressure"] = pressure;
  // Timestamp omitted on purpose -- the backend stamps server time.
  // If your ESP32 has NTP-synced time, you can add doc["timestamp"] here.

  String body;
  serializeJson(doc, body);

  int httpCode = http.POST(body);
  if (httpCode > 0) {
    String response = http.getString();
    Serial.printf("POST -> %d: %s\n", httpCode, response.c_str());
  } else {
    Serial.printf("POST failed: %s\n", http.errorToString(httpCode).c_str());
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  pinMode(VIBRATION_PIN, INPUT);
  pinMode(PRESSURE_PIN, INPUT);
  connectWiFi();
}

void loop() {
  if (millis() - lastSend >= INTERVAL_MS) {
    lastSend = millis();

    float temperature = dht.readTemperature();
    if (isnan(temperature)) {
      Serial.println("Failed to read DHT sensor, retrying next cycle.");
      return;
    }

    float vibration = readVibration();
    float pressure = readPressure();

    Serial.printf("T=%.2fC  Vib=%.2f  P=%.2f kPa\n", temperature, vibration, pressure);
    sendReading(temperature, vibration, pressure);
  }
}
