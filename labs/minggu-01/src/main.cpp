// Praktikum Minggu 1 (Lab-0) - Blocking vs Non-Blocking + serialisasi JSON
// Berdasarkan Listing 4 panduan praktikum, ditambah jawaban C6:
// tombol darurat mengganti interval telemetri 2000 ms (normal) <-> 500 ms (siaga cepat).

#include <Arduino.h>
#include <DHT.h>
#include <ArduinoJson.h>

#define PIN_DHT 4
#define TIPE_DHT DHT22
#define PIN_LED_ALERT 2
#define PIN_TOMBOL_DARURAT 15

// Ubah ke 0 untuk menguji mode BLOCKING (delay), 1 untuk NON-BLOCKING (millis)
#ifndef MODE_NON_BLOCKING
#define MODE_NON_BLOCKING 1
#endif

DHT dht(PIN_DHT, TIPE_DHT);
unsigned long waktuBacaTerakhir = 0;

// C6: interval tidak lagi konstanta tunggal, tetapi dipilih dari dua mode.
const unsigned long INTERVAL_NORMAL_MS = 2000;
const unsigned long INTERVAL_SIAGA_MS = 500;
unsigned long intervalTelemetriMs = INTERVAL_NORMAL_MS;
bool modeSiaga = false;

const float AMBANG_SUHU_C = 32.0;
unsigned long nomorPaket = 0;
bool statusTombolSebelumnya = HIGH;

void kirimTelemetriJson(float suhu, float kelembapan, bool alertSuhu) {
  JsonDocument doc;
  doc["device_id"] = "esp32-unib-node01";
  doc["seq"] = ++nomorPaket;
  doc["uptime_ms"] = millis();
  doc["mode"] = MODE_NON_BLOCKING ? "non-blocking" : "blocking";
  doc["interval_ms"] = intervalTelemetriMs;
  doc["temp_c"] = serialized(String(suhu, 2));
  doc["hum_pct"] = serialized(String(kelembapan, 2));
  doc["alert"] = alertSuhu;

  serializeJson(doc, Serial);
  Serial.println();
}

void bacaDanKirim() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (!isnan(h) && !isnan(t)) {
    bool alert = (t >= AMBANG_SUHU_C);
    digitalWrite(PIN_LED_ALERT, alert ? HIGH : LOW);
    kirimTelemetriJson(t, h, alert);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED_ALERT, OUTPUT);
  pinMode(PIN_TOMBOL_DARURAT, INPUT_PULLUP);
  dht.begin();
  Serial.println("{\"event\":\"boot\",\"msg\":\"Simpul IoT UNIB Aktif\"}");
}

void loop() {
  // 1. Pemeriksaan input tombol darurat secara kontinu
  bool statusTombol = digitalRead(PIN_TOMBOL_DARURAT);
  if (statusTombol == LOW && statusTombolSebelumnya == HIGH) {
    // C6: setiap tekanan membalik mode normal <-> siaga cepat
    modeSiaga = !modeSiaga;
    intervalTelemetriMs = modeSiaga ? INTERVAL_SIAGA_MS : INTERVAL_NORMAL_MS;

    Serial.printf("{\"event\":\"emergency_button\",\"pressed_at_ms\":%lu,\"siaga\":%s,\"interval_ms\":%lu}\n",
                  millis(), modeSiaga ? "true" : "false", intervalTelemetriMs);
    digitalWrite(PIN_LED_ALERT, !digitalRead(PIN_LED_ALERT));
    delay(50);  // Debounce singkat
  }
  statusTombolSebelumnya = statusTombol;

  // 2. Pembacaan sensor berkala: Mode Blocking vs Non-Blocking
#if MODE_NON_BLOCKING == 0
  delay(intervalTelemetriMs);  // BLOCKING: CPU berhenti total selama interval!
  bacaDanKirim();
#else
  unsigned long sekarang = millis();
  if (sekarang - waktuBacaTerakhir >= intervalTelemetriMs) {
    waktuBacaTerakhir = sekarang;
    bacaDanKirim();
  }
#endif
}
