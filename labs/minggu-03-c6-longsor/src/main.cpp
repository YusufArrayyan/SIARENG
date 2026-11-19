// Tugas C6 Modul Minggu 3: "Smart Early-Warning Landslide Node"
//
// Kebutuhan soal:
//  (a) baca BME280 via I2C setiap 15 menit memakai Timer Deep Sleep
//  (b) sensor getaran membangunkan ESP32 lewat EXT0 bila ada guncangan sebelum timer habis
//  (c) simpan 10 riwayat tekanan terakhir di RTC_DATA_ATTR untuk menghitung tren
//  (d) sinyal darurat bila tekanan turun >= 3 hPa dalam 1 jam
//
// Mesin keadaan (setiap siklus bangun selalu mulai dari setup()):
//
//   BANGUN -> TENTUKAN_PEMICU -> BACA_SENSOR -> SIMPAN_RIWAYAT -> EVALUASI
//                                                                  |
//                         +------------- aman -------------------+-+-- darurat --+
//                         v                                                     v
//                      LAPOR (JSON) -> ATUR_PEMICU -> DEEP_SLEEP          ALARM 10 dtk -> LAPOR -> ...
//
// Pin:
//   BME280  SDA 21, SCL 22 (alamat 0x76)
//   Sensor getaran SW-420  DO -> GPIO 33 (RTC GPIO, HIGH saat bergetar)
//   Buzzer  GPIO 25, LED merah GPIO 26

#include <Arduino.h>
#include <Wire.h>
#include <sys/time.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <ArduinoJson.h>

#define PIN_GETARAN GPIO_NUM_33
#define PIN_BUZZER 25
#define PIN_LED_DARURAT 26

constexpr uint64_t INTERVAL_TIDUR_US = 15ULL * 60ULL * 1000000ULL;  // 15 menit
constexpr int JUMLAH_RIWAYAT = 10;
constexpr float AMBANG_TURUN_HPA = 3.0f;      // turun >= 3 hPa ...
constexpr uint32_t JENDELA_TREN_S = 3600;     // ... dalam 1 jam
constexpr uint32_t LAMA_ALARM_MS = 10000;

struct Sampel {
  uint32_t t;        // detik sejak power-on (jam RTC tetap berjalan saat Deep Sleep)
  float tekananHpa;
};

// --- Memori RTC: bertahan selama Deep Sleep ---
RTC_DATA_ATTR Sampel riwayat[JUMLAH_RIWAYAT];
RTC_DATA_ATTR int jumlahSampel = 0;      // 0..10
RTC_DATA_ATTR int indeksTulis = 0;       // posisi tulis berikutnya (ring buffer)
RTC_DATA_ATTR uint32_t nomorSiklus = 0;
RTC_DATA_ATTR uint32_t jumlahGetaran = 0;

Adafruit_BME280 bme;

uint32_t detikSekarang() {
  timeval tv;
  gettimeofday(&tv, nullptr);
  return (uint32_t)tv.tv_sec;
}

void simpanRiwayat(uint32_t t, float p) {
  riwayat[indeksTulis] = {t, p};
  indeksTulis = (indeksTulis + 1) % JUMLAH_RIWAYAT;
  if (jumlahSampel < JUMLAH_RIWAYAT) jumlahSampel++;
}

// Penurunan tekanan terbesar dibanding sampel mana pun dalam 1 jam terakhir.
// Nilai positif = tekanan turun. Bekerja walau sampel tidak berjarak sama
// (bangun karena getaran menambah sampel di luar jadwal 15 menit).
float penurunanSatuJam(uint32_t tNow, float pNow) {
  float maksTurun = 0.0f;
  for (int i = 0; i < jumlahSampel; i++) {
    const Sampel& s = riwayat[i];
    if (tNow - s.t <= JENDELA_TREN_S && s.t < tNow) {
      maksTurun = max(maksTurun, s.tekananHpa - pNow);
    }
  }
  return maksTurun;
}

void alarmDarurat() {
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED_DARURAT, OUTPUT);
  const uint32_t mulai = millis();
  while (millis() - mulai < LAMA_ALARM_MS) {          // satu-satunya fase tunggu: sengaja,
    const bool fase = ((millis() - mulai) / 250) % 2;  // karena setelah ini ESP32 tidur
    digitalWrite(PIN_LED_DARURAT, fase);
    if (fase) tone(PIN_BUZZER, 2500); else noTone(PIN_BUZZER);
    delay(10);
  }
  noTone(PIN_BUZZER);
  digitalWrite(PIN_LED_DARURAT, LOW);
}

void setup() {
  Serial.begin(115200);
  nomorSiklus++;

  // TENTUKAN_PEMICU
  const esp_sleep_wakeup_cause_t alasan = esp_sleep_get_wakeup_cause();
  const char* pemicu = alasan == ESP_SLEEP_WAKEUP_TIMER ? "timer"
                     : alasan == ESP_SLEEP_WAKEUP_EXT0  ? "getaran"
                     : "power_on";
  if (alasan == ESP_SLEEP_WAKEUP_EXT0) jumlahGetaran++;

  // BACA_SENSOR
  Wire.begin(21, 22);
  const bool sensorOk = bme.begin(0x76);
  float suhu = NAN, lembap = NAN, tekanan = NAN;
  if (sensorOk) {
    bme.setSampling(Adafruit_BME280::MODE_FORCED, Adafruit_BME280::SAMPLING_X1,
                    Adafruit_BME280::SAMPLING_X4, Adafruit_BME280::SAMPLING_X1,
                    Adafruit_BME280::FILTER_OFF);
    bme.takeForcedMeasurement();
    suhu = bme.readTemperature();
    lembap = bme.readHumidity();
    tekanan = bme.readPressure() / 100.0f;
  }

  // SIMPAN_RIWAYAT dan EVALUASI
  const uint32_t t = detikSekarang();
  float turun = 0.0f;
  bool darurat = false;
  if (sensorOk) {
    turun = penurunanSatuJam(t, tekanan);
    darurat = turun >= AMBANG_TURUN_HPA;
    simpanRiwayat(t, tekanan);
  }

  // LAPOR
  JsonDocument doc;
  doc["device_id"] = "esp32-longsor-node01";
  doc["cycle"] = nomorSiklus;
  doc["wakeup"] = pemicu;
  doc["t_s"] = t;
  doc["sensor_ok"] = sensorOk;
  if (sensorOk) {
    doc["temp_c"] = serialized(String(suhu, 2));
    doc["hum_pct"] = serialized(String(lembap, 1));
    doc["pressure_hpa"] = serialized(String(tekanan, 2));
    doc["drop_1h_hpa"] = serialized(String(turun, 2));
  }
  doc["vibration_count"] = jumlahGetaran;
  doc["history_n"] = jumlahSampel;
  doc["alert"] = darurat || alasan == ESP_SLEEP_WAKEUP_EXT0;
  doc["alert_reason"] = darurat ? "pressure_drop" : (alasan == ESP_SLEEP_WAKEUP_EXT0 ? "vibration" : "none");
  serializeJson(doc, Serial);
  Serial.println();

  // ALARM (hanya untuk penurunan tekanan; getaran dicatat dan dilaporkan)
  if (darurat) alarmDarurat();

  // ATUR_PEMICU dan DEEP_SLEEP
  esp_sleep_enable_timer_wakeup(INTERVAL_TIDUR_US);
  // Jangan pasang EXT0 bila sensor masih bergetar: ESP32 akan langsung bangun lagi berulang-ulang.
  if (digitalRead(PIN_GETARAN) == LOW) {
    esp_sleep_enable_ext0_wakeup(PIN_GETARAN, 1);
  }
  Serial.flush();
  esp_deep_sleep_start();
}

void loop() {}
