// =====================================================================
//  Pemantau Potensi Longsor Lereng - ESP32 (non-blocking)
//  Sensor : MPU6050 (kemiringan), kelembapan tanah, sensor hujan
//  Aktuator: LED hijau/kuning/merah + buzzer
//  Keluaran: telemetri JSON per baris lewat Serial, dan lewat WiFi (HTTP POST)
//            ke backend bila KIRIM_WIFI = 1 (lihat include/jaringan.h)
//
//  Kalibrasi sensor dan uji perakitan lewat Serial Monitor: ketik "info"
//  atau lihat daftar perintah di include/kalibrasi.h.
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
#include "kalibrasi.h"

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
static int  gagalMpu = 0;                            // pembacaan gagal berturut-turut
static unsigned long tCobaMpu = 0;                   // terakhir mencoba menyambung ulang
constexpr int           BATAS_GAGAL_MPU     = 10;    // 10 x 200 ms = 2 detik
constexpr unsigned long JEDA_COBA_MPU_MS    = 5000;
constexpr unsigned long TUNGGU_TANPA_MPU_MS = 3000;  // tanpa MPU, pantau tanah + hujan saja

static char   bufPerintah[40];
static size_t panjangPerintah = 0;

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
  // Semua nol berarti modul tidak menjawab dengan benar (kabel goyang).
  return !(rx == 0 && ry == 0 && rz == 0);
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

// Uji perakitan: hijau, kuning, merah menyala bergantian lalu buzzer berbunyi singkat.
static void ujiIndikator() {
  tulisLed(true, false, false);  delay(300);
  tulisLed(false, true, false);  delay(300);
  tulisLed(false, false, true);  delay(300);
  tulisLed(false, false, false);
  buzzerSet(true);
  delay(150);
  buzzerSet(false);
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
  doc["soil_raw"]       = soilRaw;   // dipakai untuk kalibrasi kering/basah
  doc["rain_raw"]       = rainRaw;
  doc["alert"]          = (s == Status::BAHAYA);
  doc["mpu_ok"]         = mpuOk;
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

static void kirimPesan(const char* nama, const char* msg) {
  JsonDocument doc;
  doc["event"]     = nama;
  doc["device_id"] = DEVICE_ID;
  doc["uptime_ms"] = millis();
  doc["msg"]       = msg;
  keluarkan(doc);
}

static void kirimInfo() {
  const kalibrasi::Nilai& k = kalibrasi::nilai();
  JsonDocument doc;
  doc["event"]       = "info";
  doc["device_id"]   = DEVICE_ID;
  doc["mode"]        = SIMULASI ? "sim" : "real";
  doc["buzzer"]      = BUZZER_PASIF ? "pasif" : "aktif";
  doc["mpu_ok"]      = mpuOk;
  doc["soil_raw"]    = kalibrasi::rataRaw(PIN_SOIL);
  doc["rain_raw"]    = kalibrasi::rataRaw(PIN_RAIN);
  doc["soil_kering"] = k.soilKering;
  doc["soil_basah"]  = k.soilBasah;
  doc["rain_kering"] = k.rainKering;
  doc["rain_basah"]  = k.rainBasah;
#if KIRIM_WIFI
  doc["rssi"]        = jaringan::rssi();
#endif
  keluarkan(doc);
}

static unsigned long intervalTelemetri(Status s) {
  switch (s) {
    case Status::AMAN:    return INTERVAL_TELEMETRI_AMAN;
    case Status::WASPADA: return INTERVAL_TELEMETRI_WASPADA;
    default:              return INTERVAL_TELEMETRI_BAHAYA;
  }
}

// ------------------------- Kemiringan & perintah ----------------------
static void mulaiBaseline() {
  baselineSiap = false;
  sampelBaseline = 0;
  sumX = sumY = sumZ = 0;
  penilai = PenilaiStatus();   // posisi baru dianggap normal, status kembali AMAN
}

// Tanpa MPU6050, status tetap dinilai dari tanah dan hujan (kemiringan dianggap 0).
static bool siapMenilai(unsigned long now) {
  return baselineSiap || (!mpuOk && now >= TUNGGU_TANPA_MPU_MS);
}

static void jalankanPerintah(char* teks, unsigned long now) {
  for (char* c = teks; *c; ++c) *c = (char)tolower((unsigned char)*c);
  String t(teks);
  t.trim();
  if (t.isEmpty()) return;

  kalibrasi::Nilai& k = kalibrasi::nilai();
  if (t == "info") { kirimInfo(); return; }
  if (t == "tes")  { ujiIndikator(); kirimPesan("tes", "LED hijau, kuning, merah lalu buzzer sudah diuji"); return; }
  if (t == "nol")  { mulaiBaseline(); kirimEvent("kalibrasi_ulang", nullptr, nullptr, now); return; }
  if (t == "kal reset") {
    kalibrasi::reset();
    kirimPesan("kalibrasi", "kembali ke nilai bawaan config.h");
    kirimInfo();
    return;
  }

  int* tujuan = nullptr;
  int pin = -1;
  if      (t == "kal tanah kering") { tujuan = &k.soilKering; pin = PIN_SOIL; }
  else if (t == "kal tanah basah")  { tujuan = &k.soilBasah;  pin = PIN_SOIL; }
  else if (t == "kal hujan kering") { tujuan = &k.rainKering; pin = PIN_RAIN; }
  else if (t == "kal hujan basah")  { tujuan = &k.rainBasah;  pin = PIN_RAIN; }

  if (!tujuan) {
    kirimPesan("bantuan", "perintah: info | tes | nol | kal tanah kering | kal tanah basah | "
                          "kal hujan kering | kal hujan basah | kal reset");
    return;
  }
  *tujuan = kalibrasi::rataRaw(pin);
  kalibrasi::simpan();
  char msg[64];
  snprintf(msg, sizeof(msg), "%s = %d tersimpan", t.c_str() + 4, *tujuan);
  kirimPesan("kalibrasi", msg);
  if (abs(k.soilKering - k.soilBasah) < 300 || abs(k.rainKering - k.rainBasah) < 300) {
    kirimPesan("peringatan", "selisih RAW kering dan basah masih kurang dari 300. "
                             "Lengkapi pasangan kering/basah, atau cek kabel AO sensor");
  }
}

// Baca perintah dari Serial tanpa menghentikan loop.
static void bacaPerintah(unsigned long now) {
  while (Serial.available()) {
    const char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      bufPerintah[panjangPerintah] = '\0';
      if (panjangPerintah) jalankanPerintah(bufPerintah, now);
      panjangPerintah = 0;
    } else if (panjangPerintah < sizeof(bufPerintah) - 1) {
      bufPerintah[panjangPerintah++] = c;
    }
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
  analogSetAttenuation(ADC_11db);   // rentang ADC sampai ~3,3 V, sensor diberi daya dari 3V3
  kalibrasi::muat();

  ujiIndikator();                   // cek perakitan: tiga LED lalu buzzer menyala bergantian

  jaringan::mulai();

  mpuOk = mpuInit();
  tCobaMpu = millis();
  kirimEvent("boot", nullptr, nullptr, millis());
  if (!mpuOk) {
    kirimPesan("error", "MPU6050 tidak terdeteksi di I2C 0x68. Cek VCC ke 3V3, SDA ke GPIO 21, "
                        "SCL ke GPIO 22. Tanah dan hujan tetap dipantau");
  }
  kirimInfo();
  tulisLed(false, true, false);  // kuning selama kalibrasi
}

// ------------------------------ Loop ---------------------------------
void loop() {
  const unsigned long now = millis();

  // 1. Tombol: kalibrasi ulang baseline kemiringan (debounce non-blocking)
  const bool tombol = digitalRead(PIN_TOMBOL);
  if (tombol == LOW && tombolSebelumnya == HIGH && now - tTombol > DEBOUNCE_TOMBOL_MS) {
    tTombol = now;
    mulaiBaseline();
    kirimEvent("kalibrasi_ulang", nullptr, nullptr, now);
  }
  tombolSebelumnya = tombol;

  // Perintah kalibrasi dari Serial Monitor
  bacaPerintah(now);

  // 2. Baca sensor berkala (tanpa delay)
  if (now - tSensor >= INTERVAL_SENSOR_MS) {
    tSensor = now;

    soilRaw = analogRead(PIN_SOIL);
    rainRaw = analogRead(PIN_RAIN);
    const kalibrasi::Nilai& k = kalibrasi::nilai();
    const float sPct = persenDariRaw(soilRaw, k.soilKering, k.soilBasah);
    const float rPct = persenDariRaw(rainRaw, k.rainKering, k.rainBasah);
    soilPct = ALFA_FILTER * sPct + (1.0f - ALFA_FILTER) * soilPct;
    rainPct = ALFA_FILTER * rPct + (1.0f - ALFA_FILTER) * rainPct;

    float ax, ay, az;
    const bool terbaca = mpuOk && mpuBaca(ax, ay, az);
    if (mpuOk && !terbaca) {
      if (++gagalMpu >= BATAS_GAGAL_MPU) {
        mpuOk = false;               // kabel I2C lepas: lanjut pantau tanah dan hujan saja
        tCobaMpu = now;
        tiltDeltaDeg = 0;
        kirimPesan("error", "MPU6050 terputus. Cek kabel SDA/SCL. Tanah dan hujan tetap dipantau");
      }
    } else if (!mpuOk && now - tCobaMpu >= JEDA_COBA_MPU_MS) {
      tCobaMpu = now;
      if (mpuInit()) {
        mpuOk = true;
        gagalMpu = 0;
        filterSiap = false;
        mulaiBaseline();             // posisi sensor bisa berubah saat dipasang ulang
        kirimPesan("mpu_tersambung", "MPU6050 tersambung. Patokan kemiringan diukur ulang");
      }
    }

    if (terbaca) {
      gagalMpu = 0;
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

    // 3. Evaluasi status (setelah baseline siap, atau tanpa MPU setelah 3 detik)
    if (siapMenilai(now)) {
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
  if (siapMenilai(now) && now - tKirim >= intervalTelemetri(s)) {
    tKirim = now;
    kirimTelemetri(s, now);
  }

  // 5. Indikator LED dan buzzer
  if (siapMenilai(now)) {
    perbaruiIndikator(s, now);
  } else {
    tulisLed(false, true, false);   // kuning menyala selama kalibrasi, buzzer diam
    buzzerSet(false);
  }
}
