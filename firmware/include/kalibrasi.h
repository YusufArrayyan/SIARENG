#pragma once
// =====================================================================
//  kalibrasi.h - nilai RAW kering/basah sensor tanah dan hujan
//  Disimpan di memori flash ESP32 (NVS), jadi kalibrasi cukup lewat
//  Serial Monitor tanpa mengubah kode dan tanpa upload ulang.
//
//  Perintah (ketik di Serial Monitor, akhiri Enter):
//    info               tampilkan pembacaan RAW dan kalibrasi saat ini
//    kal tanah kering   probe tanah di udara atau tanah kering
//    kal tanah basah    probe tanah di tanah jenuh atau segelas air
//    kal hujan kering   panel hujan kering
//    kal hujan basah    panel hujan disiram air
//    kal reset          kembali ke nilai bawaan config.h
//    tes                uji LED dan buzzer satu per satu
//    nol                kalibrasi ulang kemiringan (sama dengan tombol)
// =====================================================================
#include <Arduino.h>
#include <Preferences.h>
#include "config.h"

namespace kalibrasi {

struct Nilai {
  int soilKering = SOIL_RAW_KERING;
  int soilBasah  = SOIL_RAW_BASAH;
  int rainKering = RAIN_RAW_KERING;
  int rainBasah  = RAIN_RAW_BASAH;
};

inline Nilai& nilai() {
  static Nilai n;
  return n;
}

// Mode simulasi dan alat asli memakai ruang simpan berbeda agar tidak saling menimpa.
inline const char* ruang() { return SIMULASI ? "kal-sim" : "kal-alat"; }

inline void muat() {
  Preferences p;
  if (!p.begin(ruang(), true)) return;   // belum pernah disimpan: pakai bawaan config.h
  Nilai& n = nilai();
  n.soilKering = p.getInt("sk", n.soilKering);
  n.soilBasah  = p.getInt("sb", n.soilBasah);
  n.rainKering = p.getInt("rk", n.rainKering);
  n.rainBasah  = p.getInt("rb", n.rainBasah);
  p.end();
}

inline void simpan() {
  Preferences p;
  if (!p.begin(ruang(), false)) return;
  const Nilai& n = nilai();
  p.putInt("sk", n.soilKering);
  p.putInt("sb", n.soilBasah);
  p.putInt("rk", n.rainKering);
  p.putInt("rb", n.rainBasah);
  p.end();
}

inline void reset() {
  Preferences p;
  if (p.begin(ruang(), false)) { p.clear(); p.end(); }
  nilai() = Nilai();
}

// Rata-rata 32 pembacaan agar nilai kalibrasi tidak terpengaruh derau ADC.
inline int rataRaw(int pin) {
  long jumlah = 0;
  for (int i = 0; i < 32; ++i) { jumlah += analogRead(pin); delayMicroseconds(200); }
  return (int)(jumlah / 32);
}

}  // namespace kalibrasi
