# Pemantau Potensi Longsor Lereng (ESP32)

Proyek UAS Teknologi IoT, Prodi S1 Informatika FT UNIB.
Alarm lokal berbasis ESP32 yang menggabungkan tiga sinyal: **kemiringan** (MPU6050),
**kelembapan tanah**, dan **intensitas hujan**. Status: `aman` -> `waspada` -> `bahaya`.

> Catatan penting: ini alat pembelajaran. Semua ambang adalah nilai awal untuk demo,
> bukan ambang longsor sungguhan, dan alat ini bukan sistem peringatan dini resmi.
> Ambang nyata harus bersumber dari kajian geologi atau instansi berwenang (BNPB, PVMBG, BPBD).

## Logika status

| Status | Syarat (nilai awal di `firmware/include/landslide_logic.h`) |
|---|---|
| BAHAYA | Tanah jenuh (>= 80%) **dan** kemiringan bergeser >= 5 derajat |
| WASPADA | Tanah jenuh saja, atau kemiringan bergeser >= 2 derajat, atau tanah basah (>= 60%) bersama hujan deras (>= 40%) |
| AMAN | selain itu |

Penyaring alarm palsu: status **naik** harus bertahan 2 detik, status **turun** harus bertahan 6 detik.
Kemiringan diukur sebagai sudut antara vektor gravitasi sekarang dan baseline (dikalibrasi 2 detik
setelah boot, atau tekan tombol di GPIO 15). Karena memakai vektor, arah pemasangan sensor bebas.

## Pin

| Fungsi | GPIO |
|---|---|
| MPU6050 SDA / SCL | 21 / 22 |
| Sensor tanah (potensiometer di Wokwi) | 34 |
| Sensor hujan (potensiometer di Wokwi) | 35 |
| LED hijau / kuning / merah (+ resistor 220 ohm) | 26 / 27 / 14 |
| Buzzer | 25 |
| Tombol kalibrasi ulang | 15 (ke GND, INPUT_PULLUP) |

## Menjalankan simulasi Wokwi

1. Buka folder `firmware/` di VS Code (ekstensi PlatformIO IDE dan Wokwi Simulator sudah terpasang, lisensi Wokwi aktif).
2. Build: ikon PlatformIO -> **Build** (hasilnya `.pio/build/esp32doit-devkit-v1/firmware.bin`).
3. Tekan `F1` -> **Wokwi: Start Simulator**.
4. Ikuti skenario di `docs/simulasi-demo.md`.

## Uji logika tanpa ESP32 (opsional)

```bash
cd firmware/test_host
g++ -std=c++17 -Wall -Wextra -I../include test_logic.cpp -o test_logic && ./test_logic
```

## Beralih ke sensor asli

Di `firmware/include/config.h`: ubah `SIMULASI` ke `0`, isi nilai `*_RAW_KERING` dan `*_RAW_BASAH`
dari pengukuran sendiri, dan ubah `BUZZER_PASIF` ke `0` bila memakai buzzer aktif.
Bagian probe sensor tanah saja yang boleh masuk tanah; papan elektroniknya tidak tahan air.

## Struktur repositori (standar PjBL)

```
iot-project-longsor/
|-- firmware/        # proyek PlatformIO + Wokwi
|-- edge-gateway/    # (tahap berikutnya) skrip Python / Raspberry Pi
|-- backend-api/     # (tahap berikutnya) FastAPI, subscriber MQTT, skema DB
|-- docker/          # (tahap berikutnya) docker-compose.yml
|-- labs/minggu-01/  # Praktikum 1: ESP32 + DHT22, blocking vs non-blocking
|-- docs/            # demo, laporan praktikum, proposal, arsitektur, threat model
`-- README.md
```

## Git (sesuai Praktikum Minggu 1)

```bash
cd iot-project-longsor
git init
git add .
git commit -m "chore: inisialisasi proyek pemantau longsor"
git branch -M main
git remote add origin https://github.com/<username>/iot-project-longsor.git
git push -u origin main
git checkout -b feat/firmware-sensor-init
```
