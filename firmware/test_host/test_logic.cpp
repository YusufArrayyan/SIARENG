// Uji logika di PC (tanpa ESP32):
//   g++ -std=c++17 -Wall -Wextra -I../include test_logic.cpp -o test_logic && ./test_logic
#include <cassert>
#include <cmath>
#include <cstdio>
#include "landslide_logic.h"

using namespace longsor;

static int lulus = 0;
#define CEK(kondisi)                                                   \
  do {                                                                 \
    if (!(kondisi)) { std::printf("GAGAL baris %d: %s\n", __LINE__, #kondisi); return 1; } \
    ++lulus;                                                           \
  } while (0)

static bool dekat(float a, float b, float tol) { return std::fabs(a - b) <= tol; }

int main() {
  const Ambang a;

  // --- persenDariRaw ---
  CEK(dekat(persenDariRaw(0, 0, 4095), 0.0f, 0.01f));
  CEK(dekat(persenDariRaw(4095, 0, 4095), 100.0f, 0.01f));
  CEK(dekat(persenDariRaw(2048, 0, 4095), 50.0f, 0.1f));
  CEK(dekat(persenDariRaw(3200, 3200, 1400), 0.0f, 0.01f));     // sensor asli: kering = RAW tinggi
  CEK(dekat(persenDariRaw(1400, 3200, 1400), 100.0f, 0.01f));
  CEK(dekat(persenDariRaw(5000, 0, 4095), 100.0f, 0.01f));      // dipotong ke 100
  CEK(dekat(persenDariRaw(-5, 0, 4095), 0.0f, 0.01f));          // dipotong ke 0

  // --- sudutAntarVektorDeg ---
  CEK(dekat(sudutAntarVektorDeg(0, 0, 1, 0, 0, 1), 0.0f, 0.01f));
  CEK(dekat(sudutAntarVektorDeg(0, 0, 1, 0, 1, 0), 90.0f, 0.01f));
  CEK(dekat(sudutAntarVektorDeg(0, 0, 1, 0, 0, -1), 180.0f, 0.01f));
  const float s5 = std::sin(5.0f * 3.14159265f / 180.0f), c5 = std::cos(5.0f * 3.14159265f / 180.0f);
  CEK(dekat(sudutAntarVektorDeg(s5, 0, c5, 0, 0, 1), 5.0f, 0.01f));
  CEK(dekat(sudutAntarVektorDeg(0, s5, c5, 0, 0, 1), 5.0f, 0.01f));   // arah miring bebas
  CEK(dekat(sudutAntarVektorDeg(0, 0, 0, 0, 0, 1), 0.0f, 0.01f));     // vektor nol aman

  // --- kandidatStatus ---
  CEK(kandidatStatus({10, 5, 0.0f}, a) == Status::AMAN);
  CEK(kandidatStatus({10, 5, 3.0f}, a) == Status::WASPADA);      // hanya bergeser
  CEK(kandidatStatus({50, 5, 6.0f}, a) == Status::WASPADA);      // miring tapi tanah belum jenuh
  CEK(kandidatStatus({85, 5, 6.0f}, a) == Status::BAHAYA);       // jenuh + miring
  CEK(kandidatStatus({85, 5, 0.0f}, a) == Status::WASPADA);      // jenuh saja
  CEK(kandidatStatus({85, 5, 3.0f}, a) == Status::WASPADA);      // jenuh + bergeser ringan
  CEK(kandidatStatus({65, 50, 0.0f}, a) == Status::WASPADA);     // basah + hujan
  CEK(kandidatStatus({65, 10, 0.0f}, a) == Status::AMAN);        // basah tanpa hujan
  CEK(kandidatStatus({80, 0, 5.0f}, a) == Status::BAHAYA);       // tepat di ambang

  // --- PenilaiStatus: naik butuh naikMs (2000) ---
  {
    PenilaiStatus p;
    CEK(!p.perbarui(Status::BAHAYA, 0, a));
    CEK(!p.perbarui(Status::BAHAYA, 1999, a));
    CEK(p.sekarang() == Status::AMAN);
    CEK(p.perbarui(Status::BAHAYA, 2000, a));
    CEK(p.sekarang() == Status::BAHAYA);
  }
  // Gangguan singkat tidak memicu alarm
  {
    PenilaiStatus p;
    p.perbarui(Status::BAHAYA, 0, a);
    p.perbarui(Status::BAHAYA, 1000, a);
    p.perbarui(Status::AMAN, 1200, a);          // kondisi kembali normal, jendela dibatalkan
    CEK(!p.perbarui(Status::BAHAYA, 1400, a));  // jendela baru
    CEK(!p.perbarui(Status::BAHAYA, 3300, a));  // baru 1900 ms sejak 1400
    CEK(p.sekarang() == Status::AMAN);
  }
  // Kandidat berganti-ganti WASPADA/BAHAYA: naik hanya ke tingkat yang bertahan (WASPADA)
  {
    PenilaiStatus p;
    p.perbarui(Status::WASPADA, 0, a);
    p.perbarui(Status::BAHAYA, 500, a);
    p.perbarui(Status::WASPADA, 1000, a);
    p.perbarui(Status::BAHAYA, 1500, a);
    CEK(p.perbarui(Status::WASPADA, 2000, a));
    CEK(p.sekarang() == Status::WASPADA);
  }
  // Turun butuh turunMs (6000)
  {
    PenilaiStatus p;
    p.perbarui(Status::BAHAYA, 0, a);
    CEK(p.perbarui(Status::BAHAYA, 2000, a));
    CEK(p.sekarang() == Status::BAHAYA);
    CEK(!p.perbarui(Status::AMAN, 3000, a));
    CEK(!p.perbarui(Status::AMAN, 8999, a));
    CEK(p.sekarang() == Status::BAHAYA);
    CEK(p.perbarui(Status::AMAN, 9000, a));
    CEK(p.sekarang() == Status::AMAN);
  }
  // Turun bertahap: BAHAYA -> WASPADA bila kandidat sempat WASPADA
  {
    PenilaiStatus p;
    p.perbarui(Status::BAHAYA, 0, a);
    p.perbarui(Status::BAHAYA, 2000, a);
    p.perbarui(Status::WASPADA, 3000, a);
    p.perbarui(Status::AMAN, 5000, a);
    CEK(p.perbarui(Status::AMAN, 9000, a));
    CEK(p.sekarang() == Status::WASPADA);
  }

  std::printf("OK: %d pemeriksaan lulus\n", lulus);
  return 0;
}
