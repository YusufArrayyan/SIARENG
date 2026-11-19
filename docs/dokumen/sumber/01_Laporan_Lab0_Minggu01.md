---
berkas: Laporan_Lab0_Minggu01_SIARENG
jenis: LAPORAN PRAKTIKUM
unit: LAB. JARINGAN & | SISTEM TERTANAM | Prodi S1 Informatika | Fakultas Teknik UNIB
judul: LAPORAN PRAKTIKUM MINGGU KE-1
subjudul: Penyiapan Toolchain, Simulator Wokwi, & Git
kolom: Kode Lab=Lab-0 (Orientasi) | Kelompok=SIARENG | Sub-CPMK=Sub-CPMK 1.1
kepala_kiri: Laporan Praktikum Minggu 1 — Teknologi IoT
kepala_kanan: Lab-0: Toolchain, Wokwi Simulator, & Git
kaki: Kelompok SIARENG · Laboratorium Jaringan Komputer & Sistem Tertanam FT UNIB
---

> **Identitas Kelompok dan Luaran Lab-0**
> Kelompok: **SIARENG (Siaga Lereng)** · Repositori: github.com/YusufArrayyan/SIARENG · Cabang: `feat/firmware-sensor-init`
> Kode program: `labs/minggu-01/` (berkas `platformio.ini`, `wokwi.toml`, `diagram.json`, `src/main.cpp`).
> Luaran: toolchain terpasang, rangkaian virtual ESP32 + DHT22 + LED + tombol, perbandingan *blocking* vs *non-blocking*, telemetri JSON, dan repositori Git dengan struktur lima folder standar.

| No | Peran Rekayasa | Nama Anggota | NPM |
|---|---|---|---|
| 1 | Device & Firmware Engineer | ........................................ | .................... |
| 2 | Back-End & Data Engineer | ........................................ | .................... |
| 3 | Security & DevOps Engineer | ........................................ | .................... |
| 4 | Dashboard Engineer & Project Manager | ........................................ | .................... |

## Bagian 1 — Ringkasan Pelaksanaan Eksperimen

| No | Tahapan | Yang Dikerjakan Kelompok | Status |
|---|---|---|---|
| 1 | Eksperimen 1: instalasi toolchain | VS Code, Python, Git, PlatformIO IDE, dan Wokwi Simulator terpasang. `firmware.bin` berhasil dikompilasi. | Selesai |
| 2 | Eksperimen 2: proyek ESP32 & Wokwi | `platformio.ini` (DHT, Adafruit Unified Sensor, ArduinoJson), `wokwi.toml`, dan `diagram.json` (DHT22 GPIO 4, LED merah + 220 Ω GPIO 2, tombol GPIO 15). | Selesai |
| 3 | Eksperimen 3: *blocking* vs *non-blocking* | Sakelar `MODE_NON_BLOCKING` (0 = `delay()`, 1 = `millis()`). Kedua mode dikompilasi tanpa galat. | Kode selesai, data diisi dari uji |
| 4 | Eksperimen 4: kolaborasi Git | Repositori dengan lima folder standar (`firmware`, `edge-gateway`, `backend-api`, `docker`, `docs`), `.gitignore`, dan cabang `feat/firmware-sensor-init`. | Selesai, *commit* tiap anggota menyusul |
| 5 | Tugas C6 | Tombol mengganti interval telemetri 2000 ms ↔ 500 ms. | Selesai |

## Bagian 2 — Rangkaian dan Kode Program

### 2.1 Pemetaan Pin yang Digunakan

| Komponen | Pin ESP32 | Keterangan |
|---|---|---|
| Sensor DHT22 | GPIO 4 | Data satu kabel, VCC ke 3V3 |
| LED merah + resistor 220 Ω | GPIO 2 | Indikator *alert* suhu ≥ 32 °C |
| Tombol darurat | GPIO 15 | `INPUT_PULLUP`, aktif LOW |
| Serial Monitor | TX0/RX0 | 115200 baud, keluaran JSON |

### 2.2 Modifikasi C6 pada Kode Eksperimen 3

```
const unsigned long INTERVAL_NORMAL_MS = 2000;
const unsigned long INTERVAL_SIAGA_MS  = 500;
unsigned long intervalTelemetriMs = INTERVAL_NORMAL_MS;
bool modeSiaga = false;

// di dalam loop(), saat tepi turun tombol terdeteksi:
modeSiaga = !modeSiaga;
intervalTelemetriMs = modeSiaga ? INTERVAL_SIAGA_MS : INTERVAL_NORMAL_MS;

// pembacaan berkala memakai variabel, bukan konstanta:
if (sekarang - waktuBacaTerakhir >= intervalTelemetriMs) { ... }
```
Listing 1: Perubahan interval telemetri lewat tombol darurat (`labs/minggu-01/src/main.cpp`)

## Bagian 3 — Lembar Pengamatan & Verifikasi Laboratorium

>! **Catatan pengisian.** Nilai dalam tanda kurung adalah perkiraan teoretis dari perilaku kode, bukan data ukur. Isi titik-titik dengan hasil pengamatan Wokwi sebelum laporan dikumpulkan.

### 3.1 Tabel Pengamatan Eksperimen 3 (*Blocking* vs *Non-Blocking*)

Prosedur: suhu DHT22 digeser dari 26 °C ke 35 °C, lalu tombol hijau ditekan 5 kali secara acak. Jeda respons dihitung dari `pressed_at_ms` pada event `emergency_button` dikurangi waktu tombol ditekan menurut jam simulasi.

| Parameter Uji | Mode *Blocking* (`delay(2000)`) | Mode *Non-Blocking* (`millis()`) | Kesimpulan Teknis |
|---|---|---|---|
| 1. Rata-rata jeda respons tombol darurat (ms) | ........ (perkiraan 0–2000 ms, rata-rata sekitar 1000 ms) | ........ (perkiraan di bawah 1 ms sampai puluhan ms) | Pada mode *blocking*, tombol hanya dibaca sekali tiap putaran `loop()` yang lamanya sekitar 2 detik. |
| 2. Keberhasilan deteksi 5 tekanan tombol cepat | ........ dari 5 (perkiraan sebagian hilang) | ........ dari 5 (perkiraan 5 dari 5) | Tekanan yang dimulai dan dilepas selama `delay()` tidak pernah terbaca. |
| 3. Contoh keluaran JSON saat suhu 35 °C | ........ (format: `"mode": "blocking", "temp_c": 35.00, "alert": true`) | ........ (format: `"mode": "non-blocking", "temp_c": 35.00, "alert": true`) | Format sama. `alert` bernilai `true` karena 35 °C melewati ambang 32 °C. Baris lengkap ditempel dari Serial Monitor. |

### 3.2 Pertanyaan Analisis Praktikum Minggu 1 (Level C1–C6)

> **[C1 – Mengingat]** Jelaskan fungsi dari masing-masing berkas konfigurasi `platformio.ini`, `wokwi.toml`, serta `diagram.json` pada proyek simulasi IoT berbasis PlatformIO–Wokwi!

- **`platformio.ini`** mengatur proses build: platform `espressif32`, papan `esp32doit-devkit-v1`, framework Arduino, kecepatan Serial Monitor 115200, dan pustaka yang otomatis diunduh lewat `lib_deps` (DHT, Adafruit Unified Sensor, ArduinoJson).
- **`wokwi.toml`** memberi tahu ekstensi Wokwi lokasi berkas hasil kompilasi, yaitu `firmware.bin` untuk dijalankan dan `firmware.elf` untuk simbol debug.
- **`diagram.json`** adalah skema rangkaian virtual: daftar komponen (`parts`) beserta posisi dan atributnya, serta kabel antarpin (`connections`), misalnya `dht1:SDA` ke `esp:D4`.

> **[C2 – Memahami]** Mengapa direktori `.pio/` dan berkas `.env` wajib dimasukkan ke dalam `.gitignore` pada repositori proyek IoT?

Direktori **`.pio/`** berisi hasil build (berkas objek, `.bin`, `.elf`) dan salinan pustaka yang diunduh. Ukurannya puluhan megabita, selalu bisa dibuat ulang dari kode sumber, dan berbeda di tiap komputer. Bila ikut di-*commit*, repositori menjadi berat dan sering terjadi *merge conflict* pada berkas biner.

Berkas **`.env`** menyimpan rahasia seperti SSID dan kata sandi Wi-Fi, kredensial *broker* MQTT, atau token API. Riwayat Git bersifat permanen, sehingga rahasia yang sudah ter-*push* tetap dapat dibaca orang lain walaupun berkasnya dihapus kemudian.

> **[C3 – Menerapkan]** Hitunglah ukuran (byte) satu baris *payload* JSON dari fungsi `kirimTelemetriJson()`! Berapa total kuota data bulanan (30 hari) jika perangkat mengirim paket tersebut setiap 2 detik tanpa henti?

Contoh satu baris *payload*:

```
{"device_id":"esp32-unib-node01","seq":1,"uptime_ms":2005,"mode":"non-blocking",
 "temp_c":35.00,"hum_pct":40.00,"alert":true}
```
Listing 2: Contoh *payload* hasil `kirimTelemetriJson()` (satu baris pada Serial Monitor, dipecah agar muat)

| Besaran | Perhitungan | Hasil |
|---|---|---|
| Panjang satu baris | 124 karakter JSON + `\r\n` dari `Serial.println()` | 126 byte |
| Jumlah paket per 30 hari | 30 × 24 × 3600 / 2 | 1.296.000 paket |
| Kuota bulanan | 126 × 1.296.000 | 163.296.000 byte ≈ 163,3 MB |

Ukuran paket bertambah sedikit seiring waktu karena digit `seq` dan `uptime_ms` bertambah, sehingga menjelang akhir bulan satu baris mencapai sekitar 139 byte dan batas atasnya sekitar 180 MB. Angka ini belum termasuk *overhead* header MQTT, TCP, IP, dan Wi-Fi.

> **[C4 – Menganalisis]** Berdasarkan data Tabel Pengamatan 3.1, mengapa penggunaan `delay(2000)` menyebabkan sebagian penekanan tombol darurat tidak terdeteksi oleh mikrokontroler?

`delay(2000)` menghentikan `loop()` selama 2 detik, sehingga `digitalRead(PIN_TOMBOL_DARURAT)` hanya dijalankan sekali tiap sekitar 2 detik. Deteksi tombol memakai tepi turun (LOW sekarang dan HIGH sebelumnya). Bila tombol ditekan lalu dilepas sebelum `delay()` selesai, saat dibaca kembali pin sudah HIGH lagi dan tekanan itu tidak pernah terlihat. Tekanan yang masih ditahan saat `delay()` berakhir memang terdeteksi, tetapi terlambat sampai 2 detik. Dengan `millis()`, `loop()` berputar ribuan kali per detik sehingga tombol diperiksa hampir terus-menerus.

> **[C5 – Mengevaluasi]** Bandingkan kelebihan dan kekurangan membangun *payload* JSON menggunakan `ArduinoJson` (`JsonDocument`) dibanding merangkai string secara manual dengan `Serial.printf()` ditinjau dari keamanan memori dan kemudahan pemeliharaan kode!

| Aspek | ArduinoJson (`JsonDocument`) | `Serial.printf()` manual |
|---|---|---|
| Keabsahan JSON | Tanda kutip, koma, dan *escape* diurus pustaka, keluaran selalu valid | Mudah salah: kurang kutip atau koma, karakter `"` di dalam string merusak format |
| Keamanan memori | Ukuran diatur pustaka; di versi 7 memori dialokasikan di *heap* dan kegagalan dapat dicek dengan `doc.overflowed()` | Tanpa alokasi dinamis, tetapi bila memakai *buffer* tetap ukurannya dihitung sendiri; kesalahan dapat memotong data atau menimbulkan *buffer overflow* |
| Pemeliharaan | Menambah *field* cukup satu baris `doc["x"] = ...`, mudah dibaca, dan dapat dipakai untuk *parsing* perintah masuk | Satu string format panjang; urutan `%` dan argumen harus cocok, tipe keliru menghasilkan data salah |
| Biaya sumber daya | Firmware lebih besar, ada *overhead* RAM dan waktu, pemakaian *heap* berulang berisiko fragmentasi | Lebih ringan dan cepat untuk pesan pendek berstruktur tetap |

Kesimpulan kelompok: untuk *payload* telemetri yang akan terus bertambah *field*-nya, ArduinoJson lebih aman dan mudah dirawat. `printf` manual hanya layak untuk pesan pendek yang tetap, misalnya event tombol.

> **[C6 – Mencipta]** Modifikasilah kode `main.cpp` Eksperimen 3 agar ketika tombol darurat ditekan, interval telemetri berubah dari 2000 ms (mode normal) menjadi 500 ms (mode siaga cepat), dan kembali ke 2000 ms jika tombol ditekan sekali lagi!

Modifikasi ditunjukkan pada Listing 1. Interval tidak lagi berupa konstanta tunggal, melainkan variabel `intervalTelemetriMs` yang dibalik oleh setiap tepi turun tombol. Event tombol juga mencetak status mode dan interval baru, dan setiap paket JSON membawa *field* `interval_ms`.

Cara uji: tekan tombol sekali, muncul `{"event":"emergency_button",...,"siaga":true,"interval_ms":500}` dan selisih `uptime_ms` antarpaket menjadi sekitar 500 ms. Tekan lagi untuk kembali ke 2000 ms. DHT22 hanya dapat membaca paling cepat tiap 2 detik, sehingga pada mode siaga paket dikirim tiap 500 ms tetapi nilai suhu baru berubah tiap sekitar 2 detik.

### 3.3 Ceklis Verifikasi Praktikum Minggu 1

| No | Komponen Unjuk Kerja yang Diverifikasi di Laboratorium | Status | Paraf Asisten |
|---|---|---|---|
| 1 | VS Code, PlatformIO IDE, dan Wokwi terpasang dan berhasil mengompilasi `firmware.bin` tanpa galat | ☑ Lulus (kedua mode) | |
| 2 | Simulasi ESP32 + DHT22 + LED + Pushbutton berjalan di Wokwi dan menampilkan JSON valid | ☐ Lulus | |
| 3 | Mampu mendemonstrasikan perbedaan respons tombol mode *blocking* dan *non-blocking* | ☐ Lulus | |
| 4 | Repositori kelompok memiliki struktur 5 folder standar dan riwayat *commit* setiap anggota | ☐ Lulus | |

**Lampiran:** tangkapan layar Serial Monitor kedua mode dan bukti C6 (ditempel setelah pengujian).
