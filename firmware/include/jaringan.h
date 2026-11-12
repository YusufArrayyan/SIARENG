#pragma once
// =====================================================================
//  jaringan.h - kirim JSON ke backend lewat WiFi (HTTP POST)
//
//  Aktif bila KIRIM_WIFI = 1 di config.h. Pengiriman berjalan di task
//  FreeRTOS terpisah, jadi loop() utama (sensor, LED, buzzer) tidak pernah
//  menunggu jaringan. Bila WiFi putus, alarm lokal tetap bekerja dan pesan
//  ditampung di antrean (pesan terlama dibuang bila antrean penuh).
// =====================================================================
#include <Arduino.h>
#include "config.h"

constexpr size_t PANJANG_PESAN = 320;   // satu baris JSON firmware < 300 byte

#if KIRIM_WIFI

#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #error "KIRIM_WIFI = 1 tetapi include/secrets.h belum ada. Salin secrets.example.h menjadi secrets.h lalu isi WiFi dan alamat server."
#endif

#include <WiFi.h>
#include <HTTPClient.h>

namespace jaringan {

static QueueHandle_t antrean = nullptr;
constexpr int KAPASITAS_ANTREAN = 24;
constexpr uint32_t TIMEOUT_HTTP_MS = 3000;
constexpr uint32_t JEDA_SAMBUNG_ULANG_MS = 10000;

static void taskKirim(void*) {
  char pesan[PANJANG_PESAN];
  uint32_t tCobaWifi = 0;
  bool pernahTersambung = false;

  for (;;) {
    if (WiFi.status() != WL_CONNECTED) {
      if (millis() - tCobaWifi >= JEDA_SAMBUNG_ULANG_MS || tCobaWifi == 0) {
        tCobaWifi = millis();
        WiFi.disconnect();
        WiFi.begin(WIFI_SSID, WIFI_PASS);
      }
      vTaskDelay(pdMS_TO_TICKS(500));
      continue;
    }
    if (!pernahTersambung) {
      pernahTersambung = true;
      Serial.printf("{\"event\":\"wifi\",\"ip\":\"%s\",\"rssi\":%d}\n",
                    WiFi.localIP().toString().c_str(), WiFi.RSSI());
    }

    if (xQueueReceive(antrean, pesan, pdMS_TO_TICKS(1000)) != pdTRUE) continue;

    HTTPClient http;
    http.setConnectTimeout(TIMEOUT_HTTP_MS);
    http.setTimeout(TIMEOUT_HTTP_MS);
    if (http.begin(SERVER_URL)) {
      http.addHeader("Content-Type", "application/json");
      if (strlen(API_KEY) > 0) http.addHeader("X-API-Key", API_KEY);
      const int kode = http.POST((uint8_t*)pesan, strlen(pesan));
      if (kode < 200 || kode >= 300) {
        Serial.printf("{\"event\":\"kirim_gagal\",\"http\":%d}\n", kode);
        vTaskDelay(pdMS_TO_TICKS(1000));   // server mati: jangan membanjiri
      }
      http.end();
    }
  }
}

inline void mulai() {
  antrean = xQueueCreate(KAPASITAS_ANTREAN, PANJANG_PESAN);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  xTaskCreatePinnedToCore(taskKirim, "kirim", 8192, nullptr, 1, nullptr, 0);
}

// Dipanggil dari loop(): tidak pernah menunggu.
inline void antrekan(const char* json) {
  if (!antrean) return;
  char pesan[PANJANG_PESAN];
  strlcpy(pesan, json, sizeof(pesan));
  if (xQueueSend(antrean, pesan, 0) != pdTRUE) {
    char buang[PANJANG_PESAN];
    xQueueReceive(antrean, buang, 0);      // antrean penuh: buang yang terlama
    xQueueSend(antrean, pesan, 0);
  }
}

inline int rssi() { return WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0; }

}  // namespace jaringan

#else   // KIRIM_WIFI == 0: semua fungsi menjadi kosong

namespace jaringan {
inline void mulai() {}
inline void antrekan(const char*) {}
inline int rssi() { return 0; }
}

#endif
