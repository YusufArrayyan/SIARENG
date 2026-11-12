#pragma once
// Salin berkas ini menjadi "secrets.h" (di folder yang sama), lalu isi.
// secrets.h tidak ikut ter-commit ke Git, jadi kata sandi WiFi tetap aman.

#define WIFI_SSID  "NamaWiFi"            // harus jaringan 2,4 GHz (ESP32 tidak bisa 5 GHz)
#define WIFI_PASS  "KataSandiWiFi"

// Alamat laptop/server yang menjalankan backend-api, diakhiri /api/telemetry.
// IP laptop: jalankan "ipconfig" di Windows, lihat "IPv4 Address".
#define SERVER_URL "http://192.168.1.10:8000/api/telemetry"

// Harus sama dengan API_KEY yang dipakai saat menjalankan backend. Kosongkan bila backend tanpa kunci.
#define API_KEY    ""
