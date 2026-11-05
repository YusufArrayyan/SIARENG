# Laporan Praktikum Minggu 1 (Lab-0): Toolchain, Wokwi, dan Git

Proyek: SIARENG (Siaga Lereng)
Kode eksperimen: [`labs/minggu-01/`](../labs/minggu-01/)

## Ringkasan pekerjaan

| Eksperimen | Hasil |
|---|---|
| 1. Instalasi toolchain | VS Code, PlatformIO IDE, dan Wokwi Simulator terpasang. Firmware dikompilasi tanpa galat. |
| 2. Proyek ESP32 dan Wokwi | `labs/minggu-01/` berisi `platformio.ini`, `wokwi.toml`, dan `diagram.json` (ESP32 + DHT22 di GPIO 4, LED merah + resistor 220 ohm di GPIO 2, tombol di GPIO 15). |
| 3. Blocking vs non-blocking | `src/main.cpp` memakai sakelar `MODE_NON_BLOCKING` (0 = `delay()`, 1 = `millis()`). Kedua mode berhasil dikompilasi. |
| 4. Git | Repositori `YusufArrayyan/SIARENG` dengan lima folder standar (`firmware`, `edge-gateway`, `backend-api`, `docker`, `docs`) dan branch `feat/firmware-sensor-init`. |

## 3.1 Tabel pengamatan (blocking vs non-blocking)

Cara mengukur: jalankan simulasi, geser suhu DHT22 dari 26 ke 35 °C, lalu tekan tombol hijau 5 kali secara acak.
Jeda respons = `pressed_at_ms` pada event `emergency_button` dikurangi waktu tombol ditekan
(lihat jam simulasi di Wokwi). Lakukan untuk `MODE_NON_BLOCKING 0`, lalu ulangi untuk `MODE_NON_BLOCKING 1`.

> Kolom bertanda _(isi)_ wajib diisi dari hasil pengukuran sendiri. Keterangan dalam kurung adalah perkiraan teoretis, bukan data ukur.

| Parameter uji | Mode blocking (`delay(2000)`) | Mode non-blocking (`millis()`) | Kesimpulan teknis |
|---|---|---|---|
| 1. Rata-rata jeda respons tombol darurat (ms) | _(isi)_ (perkiraan: 0 sampai 2000 ms, rata-rata sekitar 1000 ms) | _(isi)_ (perkiraan: di bawah 1 ms sampai puluhan ms) | Pada mode blocking, tombol hanya dibaca sekali tiap putaran `loop()` yang lamanya sekitar 2 detik. |
| 2. Keberhasilan deteksi 5 tekanan tombol cepat | _(isi)_ dari 5 (perkiraan: sebagian hilang) | _(isi)_ dari 5 (perkiraan: 5 dari 5) | Tekanan yang dimulai dan dilepas selama `delay()` tidak pernah terbaca. |
| 3. Contoh keluaran JSON saat suhu 35 °C | `{"device_id":"esp32-unib-node01","seq":5,"uptime_ms":10012,"mode":"blocking","interval_ms":2000,"temp_c":35.00,"hum_pct":60.00,"alert":true}` | `{"device_id":"esp32-unib-node01","seq":5,"uptime_ms":10000,"mode":"non-blocking","interval_ms":2000,"temp_c":35.00,"hum_pct":60.00,"alert":true}` | Format JSON sama. `alert` bernilai `true` karena 35 °C melewati ambang 32 °C. |

Contoh JSON di baris 3 adalah format yang dihasilkan kode. Ganti dengan salinan dari Serial Monitor saat pengujian.
Kolom `interval_ms` adalah tambahan dari tugas C6 dan tidak ada di Listing 4.

## 3.2 Pertanyaan analisis

### 1. [C1] Fungsi berkas konfigurasi

- **`platformio.ini`**: konfigurasi build PlatformIO. Berkas ini menentukan platform (`espressif32`), papan (`esp32doit-devkit-v1`), framework (Arduino), kecepatan Serial Monitor (115200), dan pustaka yang otomatis diunduh lewat `lib_deps` (DHT, Adafruit Unified Sensor, ArduinoJson).
- **`wokwi.toml`**: memberi tahu ekstensi Wokwi di VS Code lokasi berkas hasil kompilasi yang dijalankan, yaitu `firmware.bin` untuk eksekusi dan `firmware.elf` untuk simbol debug.
- **`diagram.json`**: skema rangkaian virtual. Isinya daftar komponen (`parts`) beserta posisi dan atributnya, serta kabel antarpin (`connections`), misalnya `dht1:SDA` ke `esp:D4`.

### 2. [C2] Mengapa `.pio/` dan `.env` masuk `.gitignore`

- **`.pio/`** berisi hasil build (berkas objek, `.bin`, `.elf`) dan salinan pustaka yang diunduh. Ukurannya besar (puluhan MB), selalu bisa dibuat ulang dari kode sumber, dan berbeda di tiap komputer. Kalau ikut di-commit, repositori jadi berat dan sering bentrok (*merge conflict*) pada berkas biner.
- **`.env`** menyimpan rahasia seperti SSID dan kata sandi WiFi, kredensial broker MQTT, atau token API. Riwayat Git bersifat permanen: rahasia yang sudah ter-push ke GitHub tetap bisa dibaca orang lain walaupun berkasnya dihapus kemudian.

### 3. [C3] Ukuran payload dan kuota bulanan

Contoh satu baris payload dari `kirimTelemetriJson()` (Listing 4):

```
{"device_id":"esp32-unib-node01","seq":1,"uptime_ms":2005,"mode":"non-blocking","temp_c":35.00,"hum_pct":40.00,"alert":true}
```

- Panjang JSON: **124 byte**, ditambah `\r\n` dari `Serial.println()` = **126 byte** per paket.
- Jumlah paket per 30 hari: 30 × 24 × 3600 / 2 = **1.296.000 paket**.
- Kuota: 126 × 1.296.000 = **163.296.000 byte ≈ 163,3 MB** (≈ 155,7 MiB).

Ukuran paket berubah sedikit: `seq` dan `uptime_ms` bertambah digitnya seiring waktu, `"blocking"` 4 byte lebih pendek dari `"non-blocking"`, dan `false` 1 byte lebih panjang dari `true`. Menjelang akhir bulan satu baris bisa mencapai sekitar 139 byte, jadi batas atasnya sekitar 180 MB.
Angka ini hanya menghitung isi payload. Bila dikirim lewat jaringan, ada tambahan *overhead* header MQTT, TCP, IP, dan WiFi, sehingga kuota sebenarnya lebih besar.

### 4. [C4] Mengapa `delay(2000)` membuat tekanan tombol hilang

`delay(2000)` menghentikan alur `loop()` selama 2 detik. Selama itu `digitalRead(PIN_TOMBOL_DARURAT)` tidak dijalankan, jadi pin tombol hanya diperiksa sekali tiap sekitar 2 detik.
Deteksi tombol memakai tepi turun (status `LOW` sekarang dan `HIGH` sebelumnya). Jika tombol ditekan lalu dilepas sebelum `delay()` selesai, saat dibaca lagi pin sudah kembali `HIGH`, sehingga tekanan itu tidak pernah terlihat.
Tekanan yang masih ditahan saat `delay()` selesai memang terdeteksi, tetapi terlambat hingga 2 detik.
Dengan `millis()`, `loop()` terus berputar ribuan kali per detik dan hanya membaca sensor saat interval tercapai, sehingga tombol diperiksa hampir terus-menerus.

### 5. [C5] ArduinoJson vs `Serial.printf()` manual

| Aspek | ArduinoJson (`JsonDocument`) | `Serial.printf()` manual |
|---|---|---|
| Keabsahan JSON | Tanda kutip, koma, dan *escape* karakter diurus pustaka, sehingga keluaran selalu JSON valid. | Mudah salah: kurang kutip atau koma, dan karakter `"` di dalam string merusak format. |
| Keamanan memori | Ukuran diatur pustaka. Di versi 7 memori dialokasikan dinamis di *heap*, dan kegagalan alokasi dapat dicek (`doc.overflowed()`). | Tidak ada alokasi dinamis. Tetapi bila memakai `snprintf` ke *buffer* tetap, ukuran *buffer* harus dihitung sendiri, dan kesalahan dapat memotong data atau menimbulkan *buffer overflow* (jika memakai `sprintf`). |
| Pemeliharaan | Menambah atau mengubah *field* cukup satu baris `doc["x"] = ...`. Kode mudah dibaca dan bisa dipakai juga untuk *parsing* perintah masuk. | Satu string format panjang yang sulit dibaca. Urutan `%` dan argumen harus cocok, dan tipe yang salah (misal `%d` untuk `unsigned long`) menghasilkan data keliru. |
| Biaya sumber daya | Ukuran firmware bertambah dan ada *overhead* RAM serta waktu proses. Pemakaian *heap* berulang dapat menyebabkan fragmentasi. | Lebih ringan dan cepat. Cocok untuk pesan pendek yang strukturnya tetap. |

Kesimpulan: untuk payload telemetri yang akan bertambah *field*-nya dan dikirim ke backend, ArduinoJson lebih aman dan mudah dirawat. `printf` manual hanya layak untuk pesan pendek dan tetap, misalnya event tombol.

### 6. [C6] Modifikasi interval 2000 ms ↔ 500 ms

Sudah diterapkan di [`labs/minggu-01/src/main.cpp`](../labs/minggu-01/src/main.cpp). Bagian intinya:

```cpp
const unsigned long INTERVAL_NORMAL_MS = 2000;
const unsigned long INTERVAL_SIAGA_MS = 500;
unsigned long intervalTelemetriMs = INTERVAL_NORMAL_MS;
bool modeSiaga = false;

// di dalam loop(), saat tepi turun tombol terdeteksi:
modeSiaga = !modeSiaga;
intervalTelemetriMs = modeSiaga ? INTERVAL_SIAGA_MS : INTERVAL_NORMAL_MS;

// pembacaan berkala memakai variabel, bukan konstanta:
if (sekarang - waktuBacaTerakhir >= intervalTelemetriMs) { ... }
```

Cara menguji: tekan tombol sekali. Muncul `{"event":"emergency_button",...,"siaga":true,"interval_ms":500}` dan selisih `uptime_ms` antarpaket menjadi sekitar 500 ms. Tekan lagi untuk kembali ke 2000 ms.

Catatan: DHT22 hanya bisa membaca paling cepat sekali tiap 2 detik. Pada mode siaga, pustaka Adafruit mengembalikan nilai terakhir yang disimpan, jadi paket dikirim tiap 500 ms tetapi nilai suhu dan kelembapan baru berubah tiap sekitar 2 detik.

## 3.3 Ceklis verifikasi

| No | Komponen | Status |
|---|---|---|
| 1 | Toolchain terpasang, `firmware.bin` terkompilasi tanpa galat | Lulus (kedua mode dikompilasi dengan PlatformIO) |
| 2 | Simulasi ESP32 + DHT22 + LED + tombol berjalan di Wokwi dengan JSON valid | Perlu didemonstrasikan di Wokwi |
| 3 | Demonstrasi perbedaan respons tombol blocking vs non-blocking | Perlu didemonstrasikan di Wokwi |
| 4 | Repositori dengan 5 folder standar dan commit dari setiap anggota | Struktur dan branch sudah ada. Setiap anggota tim perlu membuat commit sendiri |
