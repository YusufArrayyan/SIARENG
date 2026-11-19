// Praktikum Minggu 2 (Lab-1): pengendali mikro-iklim greenhouse kopi
// ADC1 terkalibrasi + moving average, histeresis relai pompa, PWM kipas, telemetri JSON.
// Berdasarkan Listing 2 panduan praktikum, ditambah tugas C6:
//   Pengaman waktu jalan maksimum pompa (Dry-Run Safety Cut-Off).

#include <Arduino.h>
#include <DHT.h>
#include <ArduinoJson.h>

// --- Pin aman ESP32 (bebas konflik ADC2 dan strapping GPIO 12) ---
#define PIN_DHT 4
#define TIPE_DHT DHT22
#define PIN_SOIL_ADC1 34      // input-only ADC1_CH6, aman saat Wi-Fi aktif
#define PIN_TOMBOL_MODE 15    // INPUT_PULLUP
#define PIN_RELAY_POMPA 26    // relai pompa + LED hijau
#define PIN_PWM_KIPAS 18      // PWM kipas / LED biru
#define PIN_LED_FAULT 2       // LED bawaan papan DOIT, berkedip saat fault

// 0 = ambang tunggal (memperlihatkan chattering), 1 = histeresis dua ambang
#ifndef GUNAKAN_HISTERESIS
#define GUNAKAN_HISTERESIS 1
#endif

// Kalibrasi dua titik sensor tanah kapasitif (milivolt). Ganti dengan hasil ukur sendiri.
const int MV_TANAH_KERING = 2650;
const int MV_TANAH_BASAH = 1100;

const float AMBANG_POMPA_ON = 35.0f;
const float AMBANG_POMPA_OFF = 60.0f;
const float AMBANG_TUNGGAL = 45.0f;

const int PWM_FREQ_HZ = 5000;
const int PWM_RES_BIT = 8;
const int PWM_KANAL = 0;

const int UKURAN_FILTER = 5;
uint32_t bufferMv[UKURAN_FILTER] = {0};
int indeksFilter = 0;
bool filterPenuh = false;

// --- C6: pengaman pompa kering ---
const unsigned long BATAS_JALAN_POMPA_MS = 15000;   // pompa nyala terus > 15 detik
const float KENAIKAN_MINIMUM_PCT = 2.0f;            // tetapi lengas naik kurang dari 2 poin
bool faultDryRun = false;                           // terkunci sampai tombol ditekan
unsigned long sejakPompaNyala = 0;
float soilSaatPompaNyala = 0.0f;

DHT dht(PIN_DHT, TIPE_DHT);
unsigned long waktuTelemetriTerakhir = 0;
unsigned long waktuDebounceTombol = 0;
const unsigned long INTERVAL_BACA_MS = 1000;

bool statusPompa = false;
bool modeOverridePaksa = false;
bool tombolSebelumnya = HIGH;
unsigned long seqPaket = 0;
unsigned long hitungTransisiRelai = 0;

void setupPwmKipas() {
#if defined(ESP_ARDUINO_VERSION) && (ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0))
  ledcAttach(PIN_PWM_KIPAS, PWM_FREQ_HZ, PWM_RES_BIT);
#else
  ledcSetup(PWM_KANAL, PWM_FREQ_HZ, PWM_RES_BIT);
  ledcAttachPin(PIN_PWM_KIPAS, PWM_KANAL);
#endif
}

void tulisPwmKipas(uint8_t duty) {
#if defined(ESP_ARDUINO_VERSION) && (ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0))
  ledcWrite(PIN_PWM_KIPAS, duty);
#else
  ledcWrite(PWM_KANAL, duty);
#endif
}

uint32_t bacaSoilMilliVoltsTerfilter() {
  uint32_t mvMentah = analogReadMilliVolts(PIN_SOIL_ADC1);
  bufferMv[indeksFilter] = mvMentah;
  indeksFilter = (indeksFilter + 1) % UKURAN_FILTER;
  if (indeksFilter == 0) filterPenuh = true;

  int jumlahSampel = filterPenuh ? UKURAN_FILTER : indeksFilter;
  uint64_t total = 0;
  for (int i = 0; i < jumlahSampel; i++) total += bufferMv[i];
  return (uint32_t)(total / jumlahSampel);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_SOIL_ADC1, INPUT);
  pinMode(PIN_TOMBOL_MODE, INPUT_PULLUP);
  pinMode(PIN_RELAY_POMPA, OUTPUT);
  pinMode(PIN_LED_FAULT, OUTPUT);
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_SOIL_ADC1, ADC_11db);

  setupPwmKipas();
  dht.begin();
  Serial.println("{\"event\":\"boot\",\"lab\":\"Lab-01 Greenhouse Kopi UNIB\"}");
}

void loop() {
  unsigned long sekarang = millis();

  // 1. Tombol (debounce 60 ms). Saat fault aktif, tombol berfungsi sebagai reset fault.
  bool bacaTombol = digitalRead(PIN_TOMBOL_MODE);
  if (bacaTombol == LOW && tombolSebelumnya == HIGH && (sekarang - waktuDebounceTombol > 60)) {
    waktuDebounceTombol = sekarang;
    if (faultDryRun) {
      faultDryRun = false;
      modeOverridePaksa = false;
      Serial.println("{\"event\":\"fault_reset\",\"fault\":\"DRY_RUN_PROTECTION\"}");
    } else {
      modeOverridePaksa = !modeOverridePaksa;
      Serial.printf("{\"event\":\"mode_change\",\"manual_override\":%s}\n",
                    modeOverridePaksa ? "true" : "false");
    }
  }
  tombolSebelumnya = bacaTombol;

  // LED fault berkedip 4 Hz tanpa delay
  digitalWrite(PIN_LED_FAULT, faultDryRun && ((sekarang / 125) % 2));

  // 2. Akuisisi dan kendali berkala (1000 ms)
  if (sekarang - waktuTelemetriTerakhir < INTERVAL_BACA_MS) return;
  waktuTelemetriTerakhir = sekarang;

  int adcRaw = analogRead(PIN_SOIL_ADC1);
  uint32_t soilMv = bacaSoilMilliVoltsTerfilter();
  float soilPct = (float)(MV_TANAH_KERING - (int)soilMv) * 100.0f
                  / (float)(MV_TANAH_KERING - MV_TANAH_BASAH);
  soilPct = constrain(soilPct, 0.0f, 100.0f);

  float suhuUdara = dht.readTemperature();
  float lembapUdara = dht.readHumidity();
  if (isnan(suhuUdara) || isnan(lembapUdara)) {
    Serial.println("{\"error\":\"Pembacaan DHT22 gagal\"}");
    return;
  }

  // Kendali pompa: fault > override manual > histeresis / ambang tunggal
  bool pompaSebelum = statusPompa;
  if (faultDryRun) {
    statusPompa = false;
  } else if (modeOverridePaksa) {
    statusPompa = true;
  } else {
#if GUNAKAN_HISTERESIS == 1
    if (soilPct < AMBANG_POMPA_ON) statusPompa = true;
    else if (soilPct >= AMBANG_POMPA_OFF) statusPompa = false;
#else
    statusPompa = (soilPct < AMBANG_TUNGGAL);
#endif
  }

  // C6: catat awal pompa menyala, lalu periksa apakah tanah ikut basah
  if (statusPompa && !pompaSebelum) {
    sejakPompaNyala = sekarang;
    soilSaatPompaNyala = soilPct;
  }
  if (statusPompa && sekarang - sejakPompaNyala > BATAS_JALAN_POMPA_MS &&
      soilPct - soilSaatPompaNyala < KENAIKAN_MINIMUM_PCT) {
    statusPompa = false;
    faultDryRun = true;
    Serial.printf("{\"event\":\"fault\",\"fault\":\"DRY_RUN_PROTECTION\",\"run_ms\":%lu,"
                  "\"soil_start\":%.1f,\"soil_now\":%.1f}\n",
                  sekarang - sejakPompaNyala, soilSaatPompaNyala, soilPct);
  }

  if (statusPompa != pompaSebelum) hitungTransisiRelai++;
  digitalWrite(PIN_RELAY_POMPA, statusPompa ? HIGH : LOW);

  // PWM kipas proporsional suhu (28,0 C -> 0%, 38,0 C -> 100%)
  int nilaiDuty = map((long)(suhuUdara * 10.0f), 280, 380, 0, 255);
  nilaiDuty = constrain(nilaiDuty, 0, 255);
  tulisPwmKipas((uint8_t)nilaiDuty);
  float fanPct = (nilaiDuty * 100.0f) / 255.0f;

  JsonDocument doc;
  doc["device_id"] = "esp32-kopi-gh01";
  doc["seq"] = ++seqPaket;
  doc["adc_raw"] = adcRaw;
  doc["soil_mv_avg"] = soilMv;
  doc["soil_pct"] = serialized(String(soilPct, 1));
  doc["temp_c"] = serialized(String(suhuUdara, 1));
  doc["air_hum_pct"] = serialized(String(lembapUdara, 1));
  doc["pump_on"] = statusPompa;
  doc["relay_switches"] = hitungTransisiRelai;
  doc["fan_pwm_pct"] = serialized(String(fanPct, 1));
  doc["ctrl_mode"] = modeOverridePaksa ? "MANUAL" : (GUNAKAN_HISTERESIS ? "HYSTERESIS" : "SINGLE_THR");
  if (faultDryRun) doc["fault"] = "DRY_RUN_PROTECTION";

  serializeJson(doc, Serial);
  Serial.println();
}
