# Laporan Praktikum Lab-2 (Minggu 3): I2C, OLED SSD1306, FreeRTOS, dan Deep Sleep

Proyek: SIARENG (Siaga Lereng)
Kode: [`labs/minggu-03/`](../labs/minggu-03/)
Branch yang disarankan panduan: `feat/lab02-i2c-oled-deepsleep`

> Kolom bertanda *(isi)* wajib diisi dari hasil Wokwi atau papan fisik. Nilai yang tertulis di sana hanya contoh format.

## Ringkasan pekerjaan

| Eksperimen | Hasil |
|---|---|
| Rangkaian | `diagram.json` sesuai Listing 2: BMP280 dan OLED berbagi SDA GPIO 21 dan SCL GPIO 22, tombol bangun di GPIO 15 (RTC GPIO), LED status di GPIO 2. |
| 1. Diagnostik I2C | `src/scanner.cpp`, dijalankan dengan `pio run -e scanner`. Program ini juga menyebut nama peranti untuk alamat yang dikenal. |
| 2. FreeRTOS | Pembacaan sensor di `setup()` (Core 1). Tampilan OLED dan JSON dikerjakan `TaskTampilanDanSerial` yang dipin ke Core 0, dengan *mutex* untuk data bersama. |
| 3. Deep Sleep | Tidur 10 detik, bangun lewat RTC Timer atau tombol EXT0 (GPIO 15 LOW). Nomor siklus dan riwayat siklus lalu disimpan di `RTC_DATA_ATTR`. |
| C6 | Rekor suhu tertinggi dan terendah di memori RTC, tampil di baris bawah OLED. |

Satu perbaikan kecil dari Listing 3: `setup()` tidak lagi menunggu task UI dengan `delay(500)` tetap, tetapi memakai semaphore `selesaiUI` (batas tunggu 1 detik). ESP32 jadi langsung tidur begitu tampilan selesai, dan tidak tidur terlalu cepat kalau transfer OLED kebetulan lambat.

Kedua environment (`esp32doit-devkit-v1` dan `scanner`) berhasil dikompilasi.

## Tabel 3.1: pemindaian alamat bus I2C

| No | Komponen | Alamat | Fungsi |
|---|---|---|---|
| 1 | BMP280 / BME280 | `0x76` *(isi bila ternyata `0x77`)* | Sensor suhu dan tekanan; dari tekanan dihitung elevasi |
| 2 | OLED SSD1306 | `0x3C` *(isi bila ternyata `0x3D`)* | Tampilan 128 × 64 untuk data cuaca dan status siklus |

## Tabel 3.2: siklus bangun-tidur dan memori RTC

Cara mengisi: biarkan simulasi berjalan untuk Boot 1–3, tekan tombol kuning sebelum 10 detik habis untuk Boot 4, lalu biarkan lagi untuk Boot 5. Ubah suhu BMP280 di Wokwi di antara siklus supaya rekor C6 ikut berubah.

| Siklus | Pemicu | Suhu (°C) | Tekanan (hPa) | Elevasi (m) | Riwayat suhu siklus lalu di RTC |
|---|---|---|---|---|---|
| Boot 1 | Power-on reset | *(isi)* | *(isi)* | *(isi)* | 0,00 (belum ada riwayat) |
| Boot 2 | Timer (10 s) | *(isi)* | *(isi)* | *(isi)* | = suhu Boot 1 |
| Boot 3 | Timer (10 s) | *(isi)* | *(isi)* | *(isi)* | = suhu Boot 2 |
| Boot 4 | Tombol EXT0 (GPIO 15) | *(isi)* | *(isi)* | *(isi)* | = suhu Boot 3 |
| Boot 5 | Timer (10 s) | *(isi)* | *(isi)* | *(isi)* | = suhu Boot 4 |

Kolom terakhir membuktikan persistensi RTC: nilainya selalu sama dengan suhu siklus sebelumnya, padahal seluruh RAM biasa dimatikan saat Deep Sleep.

## 3.2 Jawaban analisis

### C1. Arus mode aktif vs Deep Sleep

- **Mode aktif penuh:** sekitar 80–240 mA (CPU ganda dan radio aktif).
- **Deep Sleep:** sekitar 10–150 µA, atau kira-kira 1000 kali lebih kecil.

Yang dimatikan saat Deep Sleep: kedua inti CPU, seluruh SRAM utama (520 KB), radio Wi-Fi/Bluetooth, dan periferal digital. Yang tetap hidup hanya kontroler RTC, memori RTC (8 KB *slow memory*), koprosesor ULP, dan pemicu bangun (timer RTC, RTC GPIO).

### C2. Mengapa variabel biasa ter-reset, sedangkan `RTC_DATA_ATTR` tidak

Variabel global biasa berada di SRAM utama. SRAM ini kehilangan daya saat Deep Sleep. Ketika bangun, ESP32 menjalankan ulang dari awal (*reboot*), sehingga semua variabel diinisialisasi lagi ke nilai awalnya, misalnya `int counter = 0`.

Variabel bertanda `RTC_DATA_ATTR` ditempatkan oleh *linker* di **RTC Slow Memory** (8 KB). Domain daya memori ini tetap menyala selama Deep Sleep, dan isinya tidak diinisialisasi ulang ketika bangun dari tidur. Isinya hanya hilang kalau daya benar-benar dicabut atau terjadi *power-on reset*.

### C3. Arus rata-rata dan umur baterai

Diketahui: t<sub>aktif</sub> = 1 s, I<sub>aktif</sub> = 85 mA, t<sub>tidur</sub> = 899 s, I<sub>tidur</sub> = 40 µA = 0,04 mA, C = 3000 mAh, η = 0,80.

```
I_avg = (85 × 1 + 0,04 × 899) / 900
      = (85 + 35,96) / 900
      = 0,134 mA

T = (3000 × 0,80) / 0,134 = 17.857 jam ≈ 744 hari ≈ 24,8 bulan
```

Dalam praktik, umur baterai biasanya lebih pendek karena baterai Li-Ion juga kehilangan isi dengan sendirinya (*self-discharge*, 2–3% per bulan), dan regulator di papan DevKit menarik arus diam yang bisa jauh di atas 40 µA. Angka 24,8 bulan adalah batas teoretis.

### C4. Keuntungan memindahkan tampilan ke Core 0

Mengirim 1 KB buffer OLED lewat I2C 400 kHz makan waktu sekitar 25–30 ms. Jika dikerjakan di alur yang sama dengan pembacaan sensor, semua pekerjaan lain menunggu selama itu.

Dengan `xTaskCreatePinnedToCore(..., 0)`:

- Penyegaran tampilan dan serialisasi JSON berjalan di Core 0, terpisah dari alur utama di Core 1. Pembacaan sensor dan penanganan tombol tidak ikut tertahan oleh transfer grafis yang lambat.
- Data bersama dilindungi *mutex* `mutexData`, jadi task UI tidak membaca struktur `dataCuaca` yang sedang setengah ditulis.
- Catatan: kedua task tetap memakai satu bus I2C. Jika di masa depan sensor juga dibaca berkala di Core 1 sambil OLED disegarkan di Core 0, akses ke `Wire` juga harus dijaga *mutex* agar transaksi tidak bertabrakan.

### C5. EXT0 vs EXT1 untuk 3 sensor ambang muka air

| Aspek | EXT0 | EXT1 |
|---|---|---|
| Jumlah pin | Hanya 1 RTC GPIO | Beberapa RTC GPIO sekaligus (bitmask) |
| Logika | Satu pin, level tinggi atau rendah | `ANY_HIGH` (salah satu tinggi) atau `ALL_LOW` (semua rendah) |
| Mengetahui pin penyebab | Langsung, karena hanya satu pin | Bisa, lewat `esp_sleep_get_ext1_wakeup_status()` |
| Konsumsi | Menyalakan periferal RTC IO, sedikit lebih boros | Bekerja dari kontroler RTC saja, sedikit lebih hemat |

Untuk stasiun hidrologi dengan 3 sensor ambang (misalnya siaga 3, 2, dan 1), **EXT1 dengan `ESP_EXT1_WAKEUP_ANY_HIGH`** lebih tepat. Ketiga sensor bisa membangunkan ESP32, dan firmware dapat membaca sensor mana yang memicu untuk menentukan tingkat siaga. Dengan EXT0, ketiga sensor harus digabung dulu lewat gerbang OR eksternal, dan informasi sensor mana yang aktif hilang. Kelemahan EXT1 pada ESP32 generasi pertama: tidak ada pilihan "salah satu rendah", jadi sensor harus aktif-tinggi atau diberi pembalik sinyal.

### C6. Penyimpan ekstrem cuaca

Sudah diterapkan di [`labs/minggu-03/src/main.cpp`](../labs/minggu-03/src/main.cpp):

```cpp
RTC_DATA_ATTR float suhuMaks = -1000.0f;   // di luar rentang sensor (-40..85 C),
RTC_DATA_ATTR float suhuMin  =  1000.0f;   // jadi pembacaan pertama pasti menggantikan
RTC_DATA_ATTR int siklusSuhuMaks = 0, siklusSuhuMin = 0;

if (lokal.suhu > suhuMaks) { suhuMaks = lokal.suhu; siklusSuhuMaks = nomorSiklusBoot; }
if (lokal.suhu < suhuMin)  { suhuMin  = lokal.suhu; siklusSuhuMin  = nomorSiklusBoot; }
```

- Baris paling bawah OLED menampilkan `MxNN.N MnNN.N C`.
- JSON menambahkan `temp_max_c`, `temp_min_c`, serta nomor siklus kapan masing-masing rekor tercatat.
- Rekor bertahan selama alat tidur-bangun dan hanya ter-reset saat daya dicabut. Untuk menyimpan rekor melewati pemadaman daya, nilainya perlu disimpan di flash (NVS / `Preferences`). Itu di luar lingkup soal.

**Cara membuktikan:** jalankan beberapa siklus sambil mengubah suhu BMP280 di Wokwi naik dan turun. Rekor di OLED harus mengikuti nilai tertinggi dan terendah, bukan nilai terakhir. Lampirkan tangkapan layarnya.

## 3.3 Ceklis verifikasi

| No | Unjuk kerja | Status |
|---|---|---|
| 1 | I2C Scanner mendeteksi `0x76` dan `0x3C` | Program siap (`pio run -e scanner`). Perlu dijalankan di Wokwi |
| 2 | Data suhu, tekanan, dan elevasi tampil rapi di OLED | Perlu didemonstrasikan |
| 3 | Siklus Deep Sleep: bangun lewat Timer dan tombol EXT0 | Perlu didemonstrasikan |
| 4 | Variabel `RTC_DATA_ATTR` persisten | Perlu dibuktikan lewat Tabel 3.2 |
