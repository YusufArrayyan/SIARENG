#pragma once
// =====================================================================
//  config.h - semua parameter yang perlu dikalibrasi ada di sini
// =====================================================================

// 1 = simulasi Wokwi (potensiometer menggantikan sensor tanah dan hujan)
// 0 = sensor asli (kalibrasi nilai RAW di bagian bawah!)
#ifndef SIMULASI
#define SIMULASI 1
#endif

// 1 = buzzer pasif / Wokwi (dibunyikan dengan nada lewat LEDC)
// 0 = buzzer aktif (cukup HIGH/LOW)
#ifndef BUZZER_PASIF
#define BUZZER_PASIF 1
#endif

// 1 = kirim data ke backend lewat WiFi (isi dulu include/secrets.h)
// 0 = hanya lewat kabel USB (Serial). Alarm lokal bekerja di kedua mode.
#ifndef KIRIM_WIFI
#define KIRIM_WIFI 0
#endif

#define DEVICE_ID "esp32-longsor-lereng01"

// ---------------------------- Pin -----------------------------------
constexpr int PIN_SDA     = 21;   // I2C MPU6050
constexpr int PIN_SCL     = 22;
constexpr int PIN_SOIL    = 34;   // ADC1, input saja
constexpr int PIN_RAIN    = 35;   // ADC1, input saja
constexpr int PIN_LED_G   = 26;
constexpr int PIN_LED_Y   = 27;
constexpr int PIN_LED_R   = 14;
constexpr int PIN_BUZZER  = 25;
constexpr int PIN_TOMBOL  = 15;   // INPUT_PULLUP, tekan = kalibrasi ulang kemiringan

constexpr uint8_t MPU_ADDR = 0x68;

// ------------------- Kalibrasi sensor analog ------------------------
#if SIMULASI
  // Potensiometer: putar ke kanan = tanah basah / hujan deras
  constexpr int SOIL_RAW_KERING = 0;
  constexpr int SOIL_RAW_BASAH  = 4095;
  constexpr int RAIN_RAW_KERING = 0;
  constexpr int RAIN_RAW_BASAH  = 4095;
#else
  // NILAI CONTOH untuk sensor asli. Ukur sendiri:
  //   KERING = pembacaan di udara / tanah kering, BASAH = tanah jenuh / modul tersiram air.
  // Sensor kapasitif dan modul hujan membaca RAW LEBIH TINGGI saat kering.
  constexpr int SOIL_RAW_KERING = 3200;
  constexpr int SOIL_RAW_BASAH  = 1400;
  constexpr int RAIN_RAW_KERING = 4095;
  constexpr int RAIN_RAW_BASAH  = 1200;
#endif

// ---------------------------- Waktu ---------------------------------
constexpr unsigned long INTERVAL_SENSOR_MS      = 200;   // baca sensor
constexpr unsigned long INTERVAL_TELEMETRI_AMAN = 2000;
constexpr unsigned long INTERVAL_TELEMETRI_WASPADA = 1000;
constexpr unsigned long INTERVAL_TELEMETRI_BAHAYA  = 500;  // makin sering saat bahaya
constexpr int           SAMPEL_BASELINE         = 10;    // 10 x 200 ms = 2 detik
constexpr float         ALFA_FILTER             = 0.3f;  // filter EMA (0..1)
constexpr unsigned long DEBOUNCE_TOMBOL_MS      = 250;
