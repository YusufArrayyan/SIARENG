---
berkas: Laporan_Lab2_Minggu03_SIARENG
jenis: LAPORAN PRAKTIKUM
unit: LAB. JARINGAN & | SISTEM TERTANAM | Prodi S1 Informatika | Fakultas Teknik UNIB
judul: LAPORAN PRAKTIKUM MINGGU KE-3
subjudul: Bus I2C, OLED SSD1306, FreeRTOS, & Deep Sleep
kolom: Kode Lab=Lab-2 (Bobot 2%) | Kelompok=SIARENG | Sub-CPMK=Sub-CPMK 2.1
kepala_kiri: Laporan Praktikum Minggu 3 — Teknologi IoT
kepala_kanan: Lab-2: I2C, OLED SSD1306, FreeRTOS & Deep Sleep
kaki: Kelompok SIARENG · Laboratorium Jaringan Komputer & Sistem Tertanam FT UNIB
---

> **Identitas Kelompok dan Luaran Lab-2**
> Kelompok: **SIARENG (Siaga Lereng)** · Repositori: github.com/YusufArrayyan/SIARENG · Cabang: `feat/lab02-i2c-oled-deepsleep`
> Kode program: `labs/minggu-03/` dengan dua *environment* PlatformIO: `esp32doit-devkit-v1` (program utama) dan `scanner` (I2C Scanner).
> Luaran: pemindaian bus I2C, BMP280 + OLED pada bus bersama, *task* FreeRTOS di Core 0, siklus Deep Sleep Timer + EXT0, persistensi `RTC_DATA_ATTR`, dan fitur C6 Penyimpan Ekstrem Cuaca.

| No | Peran Rekayasa | Nama Anggota | NPM |
|---|---|---|---|
| 1 | Device & Firmware Engineer | ........................................ | .................... |
| 2 | Back-End & Data Engineer | ........................................ | .................... |
| 3 | Security & DevOps Engineer | ........................................ | .................... |
| 4 | Dashboard Engineer & Project Manager | ........................................ | .................... |

## Bagian 1 — Ringkasan Pelaksanaan Eksperimen

| No | Tahapan | Yang Dikerjakan Kelompok | Status |
|---|---|---|---|
| 1 | Perakitan rangkaian | BMP280 dan OLED berbagi SDA GPIO 21 dan SCL GPIO 22, tombol bangun GPIO 15 (RTC GPIO), LED status GPIO 2. | Selesai |
| 2 | Eksperimen 1: diagnostik I2C | `src/scanner.cpp`, dijalankan dengan `pio run -e scanner`; alamat yang dikenal diberi nama peranti. | Kode selesai, data diisi dari uji |
| 3 | Eksperimen 2: FreeRTOS *dual-task* | Pembacaan sensor di `setup()` (Core 1); OLED dan JSON di `TaskTampilanDanSerial` (Core 0) dengan *mutex*. | Selesai |
| 4 | Eksperimen 3: Deep Sleep | Tidur 10 detik, bangun via RTC Timer atau tombol EXT0, nomor siklus dan riwayat di `RTC_DATA_ATTR`. | Kode selesai, data diisi dari uji |
| 5 | Tugas C6 | Rekor suhu tertinggi dan terendah di memori RTC, tampil di baris bawah OLED. | Selesai |

## Bagian 2 — Rangkaian dan Kode Program

### 2.1 Pemetaan Pin dan Alamat I2C

| Komponen | Pin ESP32 | Alamat / Keterangan |
|---|---|---|
| BMP280 (SDA, SCL) | GPIO 21, GPIO 22 | `0x76`, VCC ke 3V3 |
| OLED SSD1306 128×64 (SDA, SCL) | GPIO 21, GPIO 22 | `0x3C`, bus I2C bersama |
| Tombol *wake-up* EXT0 | GPIO 15 | RTC GPIO, `INPUT_PULLUP`, bangun saat LOW |
| LED status | GPIO 2 | Menyala saat aktif, padam saat Deep Sleep |

### 2.2 Perbaikan terhadap Listing 3 Panduan

Pada Listing 3 panduan, `setup()` menunggu *task* UI dengan `delay(500)` tetap. Kelompok menggantinya dengan semaphore `selesaiUI`, sehingga ESP32 langsung tidur begitu tampilan selesai dan tidak tidur terlalu cepat bila transfer OLED kebetulan lambat.

```
// di akhir TaskTampilanDanSerial():
xSemaphoreGive(selesaiUI);
vTaskDelete(NULL);

// di setup(), menggantikan delay(500):
xTaskCreatePinnedToCore(TaskTampilanDanSerial, "TaskUI", 4096, NULL, 1, NULL, 0);
xSemaphoreTake(selesaiUI, pdMS_TO_TICKS(1000));   // tunggu maksimal 1 detik
```
Listing 1: Sinkronisasi akhir *task* UI dengan semaphore biner (`labs/minggu-03/src/main.cpp`)

## Bagian 3 — Lembar Pengamatan, Analisis C1–C6, & Verifikasi

>! **Catatan pengisian.** Titik-titik pada tabel wajib diisi dari pengamatan Wokwi atau papan fisik. Suhu BMP280 di Wokwi diubah di antara siklus agar rekor C6 ikut teruji.

### 3.1 Tabel 3.1 — Hasil Diagnostik Pemindaian Alamat Bus I2C

| No | Nama Komponen Peranti | Alamat Heksadesimal | Keterangan Fungsi pada Sistem |
|---|---|---|---|
| 1 | Sensor tekanan/suhu BMP280 | `0x76` (hasil uji: ........) | Mengukur suhu dan tekanan; dari tekanan dihitung estimasi elevasi |
| 2 | Display grafis OLED SSD1306 | `0x3C` (hasil uji: ........) | Menampilkan data cuaca, nomor siklus, pemicu bangun, dan rekor suhu |

### 3.2 Tabel 3.2 — Siklus Bangun-Tidur (*Duty Cycling*) dan Memori RTC

| Siklus | Sumber Pemicu | Suhu (°C) | Tekanan (hPa) | Elevasi (m) | Nilai Riwayat Siklus Lalu di RTC |
|---|---|---|---|---|---|
| Boot 1 | Power-on Reset | ........ | ........ | ........ | Riwayat suhu: 0,00 (belum ada) |
| Boot 2 | Timer (10 s) | ........ | ........ | ........ | Riwayat suhu: = suhu Boot 1 |
| Boot 3 | Timer (10 s) | ........ | ........ | ........ | Riwayat suhu: = suhu Boot 2 |
| Boot 4 | Tombol EXT0 (GPIO 15) | ........ | ........ | ........ | Riwayat suhu: = suhu Boot 3 |
| Boot 5 | Timer (10 s) | ........ | ........ | ........ | Riwayat suhu: = suhu Boot 4 |

Kolom terakhir membuktikan persistensi memori RTC: nilainya selalu sama dengan suhu siklus sebelumnya, padahal seluruh SRAM utama padam saat Deep Sleep.

### 3.3 Pertanyaan Analisis Laporan Praktikum Lab-2 (Level C1–C6)

> **[C1 – Mengingat]** Berapakah konsumsi arus ESP32 saat berada di mode aktif penuh dibandingkan saat berada di mode *Deep Sleep*? Komponen perangkat keras apa saja yang dimatikan pada mode *Deep Sleep*?

Mode aktif penuh menarik sekitar 80–240 mA, sedangkan Deep Sleep hanya sekitar 10–150 µA, kira-kira seribu kali lebih kecil. Pada Deep Sleep, kedua inti CPU, seluruh SRAM utama 520 KB, radio Wi-Fi/Bluetooth, dan periferal digital dimatikan. Yang tetap hidup hanya kontroler RTC, RTC Slow Memory 8 KB, koprosesor ULP, dan sumber pemicu bangun (timer RTC dan RTC GPIO).

> **[C2 – Memahami]** Mengapa variabel global biasa selalu tereset ke nol saat ESP32 bangun dari *Deep Sleep*, sedangkan variabel `RTC_DATA_ATTR` dapat mempertahankan nilainya? Di area memori fisik mana variabel tersebut disimpan?

Variabel global biasa berada di SRAM utama yang kehilangan daya selama Deep Sleep. Saat bangun, ESP32 menjalankan ulang program dari awal sehingga variabel diinisialisasi kembali ke nilai awalnya. Variabel bertanda `RTC_DATA_ATTR` ditempatkan *linker* di **RTC Slow Memory** (8 KB). Domain daya memori ini tetap menyala selama Deep Sleep dan isinya tidak diinisialisasi ulang saat bangun; nilainya baru hilang bila daya dicabut atau terjadi *power-on reset*.

> **[C3 – Menerapkan]** Jika stasiun cuaca tidur Deep Sleep 15 menit (t<sub>tidur</sub> = 899 s, I<sub>tidur</sub> = 40 µA) dan aktif 1 detik (I<sub>aktif</sub> = 85 mA), hitunglah I<sub>avg</sub> dan estimasi masa pakai baterai Li-Ion 3000 mAh (η = 0,80) dalam satuan bulan!

| Besaran | Perhitungan | Hasil |
|---|---|---|
| Arus rata-rata | I<sub>avg</sub> = (85 × 1 + 0,04 × 899) / 900 = (85 + 35,96) / 900 | 0,134 mA |
| Masa pakai | T = 3000 × 0,80 / 0,134 | 17.857 jam ≈ 744 hari |
| Dalam bulan | 744 / 30 | ≈ 24,8 bulan |

Angka ini batas teoretis. Dalam praktik umur baterai lebih pendek karena *self-discharge* Li-Ion (2–3% per bulan) dan arus diam regulator pada papan DevKit yang bisa jauh di atas 40 µA.

> **[C4 – Menganalisis]** Pengembang membuat `TaskTampilanDanSerial` yang dipin ke Core 0 dengan `xTaskCreatePinnedToCore()` sementara `setup()` berjalan di Core 1. Analisislah keuntungan pembagian tugas ini terhadap pencegahan pemblokiran pembacaan sensor oleh transmisi data grafis I2C yang lambat!

Pengiriman 1 KB buffer OLED lewat I2C 400 kHz memakan sekitar 25–30 ms. Bila dikerjakan di alur yang sama dengan pembacaan sensor, seluruh pekerjaan lain ikut menunggu. Dengan memindahkan penyegaran tampilan dan serialisasi JSON ke Core 0, pembacaan sensor dan penanganan tombol di Core 1 tidak tertahan oleh transfer grafis. Data bersama dilindungi *mutex* `mutexData` sehingga *task* UI tidak membaca struktur `dataCuaca` yang sedang setengah ditulis.

Kelompok mencatat satu batasan: kedua inti tetap memakai satu bus I2C. Bila kelak sensor dibaca berkala di Core 1 sambil OLED disegarkan di Core 0, akses ke `Wire` juga harus dijaga *mutex* agar transaksi I2C tidak bertabrakan.

> **[C5 – Mengevaluasi]** Bandingkan kelebihan dan kelemahan pemicu bangun EXT0 (pin tunggal) terhadap EXT1 (multi-pin) untuk stasiun hidrologi deteksi banjir yang memiliki 3 sensor ambang tinggi muka air terpisah!

| Aspek | EXT0 | EXT1 |
|---|---|---|
| Jumlah pin | Satu RTC GPIO | Beberapa RTC GPIO sekaligus (bitmask) |
| Logika pemicu | Satu pin, level tinggi atau rendah | `ANY_HIGH` atau `ALL_LOW` |
| Mengetahui pin penyebab | Langsung, karena hanya satu pin | Lewat `esp_sleep_get_ext1_wakeup_status()` |
| Konsumsi daya | Menyalakan periferal RTC IO, sedikit lebih boros | Dari kontroler RTC saja, sedikit lebih hemat |

Untuk tiga sensor ambang (siaga 3, 2, dan 1), kelompok merekomendasikan **EXT1 dengan `ESP_EXT1_WAKEUP_ANY_HIGH`**. Ketiga sensor dapat membangunkan ESP32 dan firmware dapat membaca sensor mana yang memicu untuk menentukan tingkat siaga. Dengan EXT0, ketiga sensor harus digabung lewat gerbang OR eksternal dan informasi sensor penyebabnya hilang. Kelemahan EXT1 pada ESP32 generasi pertama adalah tidak tersedianya mode "salah satu rendah", sehingga sensor harus aktif-tinggi atau diberi pembalik sinyal.

> **[C6 – Mencipta]** Modifikasilah kode `main.cpp` sehingga sistem memiliki fitur **Penyimpan Ekstrem Cuaca**: simpan *Suhu Tertinggi* (`suhuMaks`) dan *Suhu Terendah* (`suhuMin`) sepanjang operasi alat di memori RTC, lalu tampilkan rekor tersebut pada baris bawah layar OLED setiap kali modul bangun!

```
RTC_DATA_ATTR float suhuMaks = -1000.0f;   // di luar rentang sensor (-40..85 C)
RTC_DATA_ATTR float suhuMin  =  1000.0f;   // sehingga pembacaan pertama pasti menggantikan
RTC_DATA_ATTR int siklusSuhuMaks = 0, siklusSuhuMin = 0;

// di TaskTampilanDanSerial(), sebelum tampilan diperbarui:
if (lokal.suhu > suhuMaks) { suhuMaks = lokal.suhu; siklusSuhuMaks = nomorSiklusBoot; }
if (lokal.suhu < suhuMin)  { suhuMin  = lokal.suhu; siklusSuhuMin  = nomorSiklusBoot; }

// baris bawah OLED:
display.drawLine(0, 52, 127, 52, SSD1306_WHITE);
display.setCursor(0, 55);
display.printf("Mx%.1f Mn%.1f C", suhuMaks, suhuMin);
```
Listing 2: Fitur Penyimpan Ekstrem Cuaca pada memori RTC

JSON keluaran juga ditambah *field* `temp_max_c`, `temp_min_c`, `temp_max_boot`, dan `temp_min_boot`. Rekor bertahan selama siklus tidur-bangun dan baru hilang bila daya dicabut; penyimpanan permanen melewati pemadaman memerlukan NVS (`Preferences`), di luar lingkup soal. Cara uji: jalankan beberapa siklus sambil menaikkan dan menurunkan suhu BMP280 di Wokwi, lalu pastikan rekor di OLED mengikuti nilai tertinggi dan terendah, bukan nilai terakhir.

### 3.4 Ceklis Verifikasi Praktikum Lab-2

| No | Unjuk Kerja yang Diverifikasi Asisten Laboratorium | Status | Paraf Asisten |
|---|---|---|---|
| 1 | Pemindaian I2C mendeteksi kedua peranti (`0x76` dan `0x3C`) pada bus bersama SDA/SCL | ☐ Lulus | |
| 2 | Suhu, tekanan, dan elevasi tampil rapi pada layar OLED SSD1306 | ☐ Lulus | |
| 3 | Siklus Deep Sleep berjalan: tertidur berkala dan terbangun via Timer maupun tombol EXT0 | ☐ Lulus | |
| 4 | Variabel `RTC_DATA_ATTR` terbukti persisten (nomor boot dan riwayat bertambah) | ☐ Lulus | |

**Lampiran:** tangkapan layar I2C Scanner, layar OLED, Serial Monitor lima siklus, dan bukti C6 (ditempel setelah pengujian).
