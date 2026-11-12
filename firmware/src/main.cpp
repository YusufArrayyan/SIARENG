// =====================================================================
//  Pemantau Potensi Longsor Lereng - ESP32 (non-blocking)
//  Sensor : MPU6050 (kemiringan), kelembapan tanah, sensor hujan
//  Aktuator: LED hijau/kuning/merah + buzzer
//  Keluaran: telemetri JSON per baris lewat Serial, dan lewat WiFi (HTTP POST)
//            ke backend bila KIRIM_WIFI = 1 (lihat include/jaringan.h)
//
//  CATATAN: ini alarm lokal untuk pembelajaran. Ambang adalah nilai awal
//  dan BUKAN ambang longsor sungguhan. Bukan sistem peringatan dini resmi.
// =====================================================================
#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include "config.h"
#include "landslide_logic.h"
#include "jaringan.h"

using namespace longsor;

// ------------------------- Keadaan global ----------------------------
static Ambang ambang;
static PenilaiStatus penilai;

static float soilPct = 0, rainPct = 0, tiltDeltaDeg = 0;
static int soilRaw = 0, rainRaw = 0;   // ADC mentah, untuk kalibrasi sensor asli
static float fax = 0, fay = 0, faz = 1;          // percepatan terfilter (g)
static float bx = 0, by = 0, bz = 1;             // vektor baseline
static bool  filterSiap = false;

static bool  baselineSiap = false;
static int   sampelBaseline = 0;
static float sumX = 0, sumY = 0, sumZ = 0;

static unsigned long tSensor = 0, tKirim = 0, tTombol = 0;
static unsigned long nomorPaket = 0;
static bool tombolSebelumnya = HIGH;
static bool mpuOk = false;

// ------------------------------ Buzzer -------------------------------
static void buzzerSetup() {
#if BUZZER_PASIF
  #if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
    ledcAttach(PIN_BUZZER, 2000, 8);
  #else
    ledcSetup(0, 2000, 8);
    ledcAttachPin(PIN_BUZZER, 0);
  #endif
#else
  pinMode(PIN_BUZZER, OUTPUT);
#endif
}

static void buzzerSet(bool nyala) {
#if BUZZER_PASIF
  const uint32_t nada = nyala ? 2000 : 0;
  #if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
    ledcWriteTone(PIN_BUZZER, nada);
  #else
    ledcWriteTone(0, nada);
  #endif
#else
  digitalWrite(PIN_BUZZER, nyala ? HIGH : LOW);
#endif
}

// ------------------------------ MPU6050 ------------------------------
static bool mpuInit() {
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);  // PWR_MGMT_1
  Wire.write(0x00);  // bangunkan sensor
  if (Wire.endTransmission() != 0) return false;
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1C);  // ACCEL_CONFIG
  Wire.write(0x00);  // +-2 g (16384 LSB/g)
  return Wire.endTransmission() == 0;
}

static int16_t bacaInt16() {
  const uint8_t hi = Wire.read();
  const uint8_t lo = Wire.read();
  return (int16_t)((hi << 8) | lo);
}

static bool mpuBaca(float& ax, float& ay, float& az) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);  // ACCEL_XOUT_H
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((uint16_t)MPU_ADDR, (uint8_t)6, true) != 6) return false;
  const int16_t rx = bacaInt16();
  const int16_t ry = bacaInt16();
  const int16_t rz = bacaInt16();
  ax = rx / 16384.0f;
  ay = ry / 16384.0f;
  az = rz / 16384.0f;
  return true;
}

// ------------------------------ Indikator ----------------------------
static void tulisLed(bool g, bool y, bool r) {
  digitalWrite(PIN_LED_G, g);
  digitalWrite(PIN_LED_Y, y);
  digitalWrite(PIN_LED_R, r);
}

// Pola non-blocking berdasarkan status dan waktu.
static void perbaruiIndikator(Status s, unsigned long now) {
  switch (s) {
    case Status::AMAN:
      tulisLed(true, false, false);
      buzzerSet(false);
      break;
    case Status::WASPADA:
      tulisLed(false, true, false);
      buzzerSet((now % 3000UL) < 100UL);          // bip pendek tiap 3 detik
      break;
    case Status::BAHAYA: {
      const bool fase = (now % 500UL) < 250UL;    // kedip 2 Hz
      tulisLed(false, false, fase);
      buzzerSet(fase);
      break;
    }
  }
}

// ------------------------------ JSON ---------------------------------
static float bulat1(float x) { return roundf(x * 10.0f) / 10.0f; }

// Satu pintu keluar: cetak ke Serial dan (bila aktif) antrekan untuk dikirim lewat WiFi.
static void keluarkan(const JsonDocument& doc) {
  char buf[PANJANG_PESAN];
  serializeJson(doc, buf, sizeof(buf));
  Serial.println(buf);
  jaringan::antrekan(buf);
}

static void kirimTelemetri(Status s, unsigned long now) {
  JsonDocument doc;
  doc["device_id"]      = DEVICE_ID;
  doc["seq"]            = ++nomorPaket;
  doc["uptime_ms"]      = now;
  doc["mode"]           = SIMULASI ? "sim" : "real";
  doc["status"]         = namaStatus(s);
  doc["soil_pct"]       = bulat1(soilPct);
  doc["rain_pct"]       = bulat1(rainPct);
  doc["tilt_delta_deg"] = bulat1(tiltDeltaDeg);
  doc["soil_raw"]       = soilRaw;   // dipakai untuk mengisi *_RAW_KERING / *_RAW_BASAH
  doc["rain_raw"]       = rainRaw;
  doc["alert"]          = (s == Status::BAHAYA);
#if KIRIM_WIFI
  doc["rssi"]           = jaringan::rssi();   // kuat sinyal WiFi (dBm), 0 = belum tersambung
#endif
  keluarkan(doc);
}

static void kirimEvent(const char* nama, const char* dari, const char* ke, unsigned long now) {
  JsonDocument doc;
  doc["event"]     = nama;
  doc["device_id"] = DEVICE_ID;
  doc["uptime_ms"] = now;
  if (dari) doc["from"] = dari;
  if (ke)   doc["to"]   = ke;
  keluarkan(doc);
}

static unsigned long intervalTelemetri(Status s) {
  switch (s) {
    case Status::AMAN:    return INTERVAL_TELEMETRI_AMAN;
    case Status::WASPADA: return INTERVAL_TELEMETRI_WASPADA;
    default:              return INTERVAL_TELEMETRI_BAHAYA;
  }
}

// ------------------------------ Setup --------------------------------
void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED_G, OUTPUT);
  pinMode(PIN_LED_Y, OUTPUT);
  pinMode(PIN_LED_R, OUTPUT);
  pinMode(PIN_TOMBOL, INPUT_PULLUP);
  buzzerSetup();
  analogReadResolution(12);

  jaringan::mulai();

  mpuOk = mpuInit();
  kirimEvent("boot", nullptr, nullptr, millis());
  if (!mpuOk) {
    JsonDocument doc;
    doc["event"] = "error";
    doc["device_id"] = DEVICE_ID;
    doc["msg"] = "MPU6050 tidak terdeteksi di I2C 0x68";
    keluarkan(doc);
  }
  tulisLed(false, true, false);  // kuning selama kalibrasi
}

// ------------------------------ Loop ---------------------------------
void loop() {
  const unsigned long now = millis();

  // 1. Tombol: kalibrasi ulang baseline kemiringan (debounce non-blocking)
  const bool tombol = digitalRead(PIN_TOMBOL);
  if (tombol == LOW && tombolSebelumnya == HIGH && now - tTombol > DEBOUNCE_TOMBOL_MS) {
    tTombol = now;
    baselineSiap = false;
    sampelBaseline = 0;
    sumX = sumY = sumZ = 0;
    penilai = PenilaiStatus();   // posisi baru dianggap normal, status kembali AMAN
    kirimEvent("kalibrasi_ulang", nullptr, nullptr, now);
  }
  tombolSebelumnya = tombol;

  // 2. Baca sensor berkala (tanpa delay)
  if (now - tSensor >= INTERVAL_SENSOR_MS) {
    tSensor = now;

    soilRaw = analogRead(PIN_SOIL);
    rainRaw = analogRead(PIN_RAIN);
    const float sPct = persenDariRaw(soilRaw, SOIL_RAW_KERING, SOIL_RAW_BASAH);
    const float rPct = persenDariRaw(rainRaw, RAIN_RAW_KERING, RAIN_RAW_BASAH);
    soilPct = ALFA_FILTER * sPct + (1.0f - ALFA_FILTER) * soilPct;
    rainPct = ALFA_FILTER * rPct + (1.0f - ALFA_FILTER) * rainPct;

    float ax, ay, az;
    if (mpuOk && mpuBaca(ax, ay, az)) {
      if (!filterSiap) { fax = ax; fay = ay; faz = az; filterSiap = true; }
      fax = ALFA_FILTER * ax + (1.0f - ALFA_FILTER) * fax;
      fay = ALFA_FILTER * ay + (1.0f - ALFA_FILTER) * fay;
      faz = ALFA_FILTER * az + (1.0f - ALFA_FILTER) * faz;

      if (!baselineSiap) {
        sumX += fax; sumY += fay; sumZ += faz;
        if (++sampelBaseline >= SAMPEL_BASELINE) {
          bx = sumX / SAMPEL_BASELINE;
          by = sumY / SAMPEL_BASELINE;
          bz = sumZ / SAMPEL_BASELINE;
          baselineSiap = true;
          kirimEvent("baseline_siap", nullptr, nullptr, now);
        }
        tiltDeltaDeg = 0;
      } else {
        tiltDeltaDeg = sudutAntarVektorDeg(fax, fay, faz, bx, by, bz);
      }
    }

    // 3. Evaluasi status (hanya setelah baseline siap)
    if (baselineSiap) {
      const Pembacaan p{soilPct, rainPct, tiltDeltaDeg};
      const Status sebelum = penilai.sekarang();
      if (penilai.perbarui(kandidatStatus(p, ambang), now, ambang)) {
        kirimEvent("status_change", namaStatus(sebelum), namaStatus(penilai.sekarang()), now);
        kirimTelemetri(penilai.sekarang(), now);   // kirim segera saat status berubah
        tKirim = now;
      }
    }
  }

  // 4. Telemetri berkala; makin sering saat status naik
  const Status s = penilai.sekarang();
  if (baselineSiap && now - tKirim >= intervalTelemetri(s)) {
    tKirim = now;
    kirimTelemetri(s, now);
  }

  // 5. Indikator LED dan buzzer
  if (baselineSiap) {
    perbaruiIndikator(s, now);
  } else {
    tulisLed(false, true, false);   // kuning menyala selama kalibrasi, buzzer diam
    buzzerSet(false);
  }
}
