#pragma once
// =====================================================================
//  landslide_logic.h - logika murni (tanpa Arduino) agar bisa diuji di PC
//  Semua ambang adalah NILAI AWAL untuk demo. Ambang longsor sungguhan
//  harus berasal dari kajian geologi / BNPB / PVMBG dan dikalibrasi di lokasi.
// =====================================================================
#include <math.h>
#include <stdint.h>

namespace longsor {

enum class Status : uint8_t { AMAN = 0, WASPADA = 1, BAHAYA = 2 };

inline const char* namaStatus(Status s) {
  switch (s) {
    case Status::AMAN:    return "aman";
    case Status::WASPADA: return "waspada";
    default:              return "bahaya";
  }
}

struct Ambang {
  float soilWaspadaPct = 60.0f;   // tanah mulai basah
  float soilJenuhPct   = 80.0f;   // tanah jenuh
  float rainWaspadaPct = 40.0f;   // hujan cukup deras
  float tiltWaspadaDeg = 2.0f;    // pergeseran kemiringan awal
  float tiltBahayaDeg  = 5.0f;    // pergeseran kemiringan berarti
  unsigned long naikMs  = 2000;   // kondisi harus bertahan sekian ms sebelum status NAIK
  unsigned long turunMs = 6000;   // ... sebelum status TURUN
};

struct Pembacaan {
  float soilPct;        // 0..100
  float rainPct;        // 0..100
  float tiltDeltaDeg;   // sudut antara vektor gravitasi sekarang dan baseline
};

// Ubah pembacaan ADC mentah menjadi persen (0 = kering, 100 = basah).
inline float persenDariRaw(int raw, int rawKering, int rawBasah) {
  if (rawKering == rawBasah) return 0.0f;
  float p = 100.0f * (float)(raw - rawKering) / (float)(rawBasah - rawKering);
  if (p < 0.0f) p = 0.0f;
  if (p > 100.0f) p = 100.0f;
  return p;
}

// Sudut (derajat) antara dua vektor percepatan. Tidak bergantung arah pemasangan sensor.
inline float sudutAntarVektorDeg(float ax, float ay, float az,
                                 float bx, float by, float bz) {
  const float na = sqrtf(ax * ax + ay * ay + az * az);
  const float nb = sqrtf(bx * bx + by * by + bz * bz);
  if (na < 1e-6f || nb < 1e-6f) return 0.0f;
  float c = (ax * bx + ay * by + az * bz) / (na * nb);
  if (c > 1.0f) c = 1.0f;
  if (c < -1.0f) c = -1.0f;
  return acosf(c) * 180.0f / 3.14159265358979f;
}

// Status "mentah" dari satu pembacaan. BAHAYA hanya bila tanah jenuh DAN kemiringan bergeser berarti.
inline Status kandidatStatus(const Pembacaan& p, const Ambang& a) {
  const bool basah    = p.soilPct      >= a.soilWaspadaPct;
  const bool jenuh    = p.soilPct      >= a.soilJenuhPct;
  const bool hujan    = p.rainPct      >= a.rainWaspadaPct;
  const bool bergeser = p.tiltDeltaDeg >= a.tiltWaspadaDeg;
  const bool miring   = p.tiltDeltaDeg >= a.tiltBahayaDeg;

  if (jenuh && miring) return Status::BAHAYA;
  if (jenuh || bergeser || (basah && hujan)) return Status::WASPADA;
  return Status::AMAN;
}

// Penyaring status: naik harus bertahan naikMs, turun harus bertahan turunMs.
// Tujuannya menekan alarm palsu (misalnya sensor tersenggol sebentar).
class PenilaiStatus {
 public:
  Status sekarang() const { return sekarang_; }

  // Mengembalikan true bila status resmi berubah pada pemanggilan ini.
  bool perbarui(Status kandidat, unsigned long nowMs, const Ambang& a) {
    const uint8_t k = static_cast<uint8_t>(kandidat);
    const uint8_t s = static_cast<uint8_t>(sekarang_);

    if (k == s) {
      naikAktif_ = false;
      turunAktif_ = false;
      return false;
    }
    if (k > s) {
      turunAktif_ = false;
      if (!naikAktif_) {
        naikAktif_ = true;
        sejakNaik_ = nowMs;
        minNaik_ = k;
      } else if (k < minNaik_) {
        minNaik_ = k;  // naik hanya sampai tingkat yang bertahan sepanjang jendela
      }
      if (nowMs - sejakNaik_ >= a.naikMs) {
        sekarang_ = static_cast<Status>(minNaik_);
        naikAktif_ = false;
        return true;
      }
    } else {
      naikAktif_ = false;
      if (!turunAktif_) {
        turunAktif_ = true;
        sejakTurun_ = nowMs;
        maksTurun_ = k;
      } else if (k > maksTurun_) {
        maksTurun_ = k;
      }
      if (nowMs - sejakTurun_ >= a.turunMs) {
        sekarang_ = static_cast<Status>(maksTurun_);
        turunAktif_ = false;
        return true;
      }
    }
    return false;
  }

 private:
  Status sekarang_ = Status::AMAN;
  bool naikAktif_ = false, turunAktif_ = false;
  unsigned long sejakNaik_ = 0, sejakTurun_ = 0;
  uint8_t minNaik_ = 0, maksTurun_ = 0;
};

}  // namespace longsor
