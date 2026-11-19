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
| LED hijau / kuning / merah (+ resistor 200–330 ohm) | 26 / 27 / 14 |
| Buzzer | 25 |
| Tombol kalibrasi ulang | 15 (ke GND, INPUT_PULLUP) |

## Menjalankan simulasi Wokwi

1. Buka folder `firmware/` di VS Code (ekstensi PlatformIO IDE dan Wokwi Simulator sudah terpasang, lisensi Wokwi aktif).
2. Dari terminal folder `firmware/`, jalankan `pio run -e wokwi` (hasilnya `.pio/build/wokwi/firmware.bin`).
3. Tekan `F1` -> **Wokwi: Start Simulator**.
4. Ikuti skenario di `docs/simulasi-demo.md`. Untuk mengirim data simulasi ke dashboard, ikuti bagian Wokwi di [`backend-api/README.md`](backend-api/README.md).

## Uji logika tanpa ESP32 (opsional)

```bash
cd firmware/test_host
g++ -std=c++17 -Wall -Wextra -I../include test_logic.cpp -o test_logic && ./test_logic
```

## Tugas praktikum dan modul

| Minggu | Kode | Laporan dan jawaban |
|---|---|---|
| 1 (Lab-0) | `labs/minggu-01/` | `docs/laporan-minggu-01.md`, `docs/tugas-minggu-01.md` (LK-1 Kasus A, problem set C1–C6) |
| 2 (Lab-1) | `labs/minggu-02/` | `docs/laporan-lab01-minggu-02.md`, `docs/tugas-minggu-02.md` (WDM Kasus B, problem set, spesifikasi SIARENG) |
| 3 (Lab-2) | `labs/minggu-03/`, `labs/minggu-03-c6-longsor/` | `docs/laporan-lab02-minggu-03.md`, `docs/tugas-minggu-03.md` |

## Barang sudah datang?

Ikuti [`docs/sambungkan-alat.md`](docs/sambungkan-alat.md): susunan breadboard dan kabel untuk komponen yang dibeli,
upload target `alat` (tanpa mengubah kode), kalibrasi sensor lewat Serial Monitor, lalu klik ganda
`backend-api/jalankan.bat` untuk membuka dashboard. Daftar belanja ada di `docs/Daftar_Belanja_Shopee_SIARENG.xlsx`.

| Target PlatformIO | Untuk |
|---|---|
| `wokwi` | Simulator Wokwi (potensiometer, kirim lewat gateway Wokwi) |
| `esp32doit-devkit-v1`, `esp32doit-devkit-v1-wifi` | ESP32 fisik dengan potensiometer (mode simulasi) |
| `alat` | Alat asli lewat USB: sensor asli, buzzer aktif |
| `alat-wifi` | Alat asli lewat WiFi (isi `include/secrets.h`) |

## Mulai dari mana?

Belum pernah merakit alat IoT? Ikuti [`docs/panduan-pemula.md`](docs/panduan-pemula.md): 10 langkah dari memasang
program di laptop, simulasi, merakit di breadboard, sampai data tampil di dashboard lewat WiFi.

## Dashboard monitoring

Pantau status lereng dari laptop atau HP. Buka `dashboard/index.html` untuk mode demo, atau jalankan
backend agar dashboard menampilkan data asli dari ESP32 lewat USB atau WiFi. Firmware menyediakan target WiFi terpisah untuk Wokwi dan ESP32 fisik. Petunjuk koneksi lengkap ada di [`backend-api/README.md`](backend-api/README.md).

## Merakit alat asli

Panduan lengkap dari breadboard sampai terpasang di lereng (catu daya surya, box IP65, kalibrasi):
[`docs/panduan-perakitan.md`](docs/panduan-perakitan.md). Anggaran ada di `docs/RAB_SIARENG.xlsx`
(lengkap) dan `docs/RAB_SIARENG_hemat.xlsx` (uji prototipe).

## Beralih ke sensor asli

Upload target `alat` atau `alat-wifi`; keduanya sudah memakai `SIMULASI=0` dan `BUZZER_PASIF=0`.
Nilai kering/basah sensor dikalibrasi lewat Serial Monitor (`kal tanah kering`, `kal tanah basah`, dst.)
dan tersimpan di memori ESP32, jadi tidak perlu mengubah kode.
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
