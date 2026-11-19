---
berkas: Laporan_Lab1_Minggu02_SIARENG
jenis: LAPORAN PRAKTIKUM
unit: LAB. JARINGAN & | SISTEM TERTANAM | Prodi S1 Informatika | Fakultas Teknik UNIB
judul: LAPORAN PRAKTIKUM MINGGU KE-2
subjudul: GPIO Digital/Analog, PWM, DHT22, & Soil Moisture
kolom: Kode Lab=Lab-1 (Bobot 2%) | Kelompok=SIARENG | Sub-CPMK=Sub-CPMK 1.2
kepala_kiri: Laporan Praktikum Minggu 2 — Teknologi IoT
kepala_kanan: Lab-1: GPIO, ADC, PWM, DHT22, & Soil Moisture
kaki: Kelompok SIARENG · Laboratorium Jaringan Komputer & Sistem Tertanam FT UNIB
---

> **Identitas Kelompok dan Luaran Lab-1**
> Kelompok: **SIARENG (Siaga Lereng)** · Repositori: github.com/YusufArrayyan/SIARENG · Cabang: `feat/lab01-sensor-actuator`
> Kode program: `labs/minggu-02/` (berkas `platformio.ini`, `wokwi.toml`, `diagram.json`, `src/main.cpp`).
> Luaran: rangkaian pin aman, pembacaan ADC1 terkalibrasi dengan *moving average*, uji *chattering* vs histeresis, PWM kipas, telemetri JSON, dan fitur tambahan C6 *Dry-Run Safety Cut-Off*.

| No | Peran Rekayasa | Nama Anggota | NPM |
|---|---|---|---|
| 1 | Device & Firmware Engineer | ........................................ | .................... |
| 2 | Back-End & Data Engineer | ........................................ | .................... |
| 3 | Security & DevOps Engineer | ........................................ | .................... |
| 4 | Dashboard Engineer & Project Manager | ........................................ | .................... |

## Bagian 1 — Ringkasan Pelaksanaan Eksperimen

| No | Tahapan | Yang Dikerjakan Kelompok | Status |
|---|---|---|---|
| 1 | Pemeriksaan rangkaian & pinout | Rangkaian disusun sesuai Listing 1 panduan. Sensor analog di GPIO 34 (ADC1), DHT22 di GPIO 4, tombol GPIO 15, relai GPIO 26, PWM GPIO 18. Tidak ada beban di GPIO 12. | Selesai |
| 2 | Eksperimen 1: karakterisasi ADC1 | `analogReadMilliVolts()`, *moving average* N = 5, pemetaan terbalik 2650 mV (0%) sampai 1100 mV (100%). | Kode selesai, data diisi dari uji |
| 3 | Eksperimen 2: uji histeresis relai | Sakelar `GUNAKAN_HISTERESIS` 0 (ambang tunggal 45%) dan 1 (35%–60%). Kedua mode berhasil dikompilasi. | Kode selesai, data diisi dari uji |
| 4 | Eksperimen 3: PWM & JSON | PWM `LEDC` 5 kHz 8 bit proporsional suhu 28–38 °C, tombol *override*, telemetri JSON per detik. | Selesai |
| 5 | Tugas C6 | Pengaman pompa kering: pompa dimatikan dan dikunci bila menyala > 15 detik tanpa kenaikan lengas. | Selesai |

## Bagian 2 — Rangkaian dan Kode Program

### 2.1 Pemetaan Pin yang Digunakan

| Komponen | Pin ESP32 | Alasan Pemilihan Pin |
|---|---|---|
| Capacitive Soil Moisture (Wokwi: potensiometer) | GPIO 34 | ADC1, input saja, tetap terbaca saat Wi-Fi aktif |
| DHT22 | GPIO 4 | Pin serbaguna, protokol satu kabel |
| Tombol *override* / reset fault | GPIO 15 | `INPUT_PULLUP`, aktif LOW, aman untuk *strapping* |
| Relai pompa + LED hijau | GPIO 26 | Keluaran digital aman, bukan pin *strapping* |
| LED biru (emulator kipas PWM) | GPIO 18 | Mendukung PWM `LEDC` |
| LED fault (bawaan papan) | GPIO 2 | Indikator kedip saat fault C6 |

### 2.2 Potongan Kode Inti

```
uint32_t bacaSoilMilliVoltsTerfilter() {
  uint32_t mvMentah = analogReadMilliVolts(PIN_SOIL_ADC1);
  bufferMv[indeksFilter] = mvMentah;
  indeksFilter = (indeksFilter + 1) % UKURAN_FILTER;
  if (indeksFilter == 0) filterPenuh = true;
  int jumlahSampel = filterPenuh ? UKURAN_FILTER : indeksFilter;
  uint64_t total = 0;
  for (int i = 0; i < jumlahSampel; i++) total += bufferMv[i];
  return (uint32_t)(total / jumlahSampel);
}
```
Listing 1: Filter *moving average* N = 5 pada pembacaan milivolt ADC1 (`labs/minggu-02/src/main.cpp`)

## Bagian 3 — Lembar Pengamatan, Analisis C1–C6, & Verifikasi

>! **Catatan pengisian.** Nilai bertanda *(perkiraan)* dihitung dari rumus pada kode program, belum diukur. Ganti dengan hasil pengamatan Wokwi atau papan fisik sebelum laporan dikumpulkan.

### 3.1 Tabel 3.1 — Karakterisasi ADC1 (GPIO 34) dan Pemetaan Kelembapan Tanah

Pemetaan bersifat terbalik, sehingga kondisi kering diperoleh dengan memutar potensiometer ke tegangan tinggi. Tegangan target tiap baris dihitung dari soil_pct = (2650 − mV) × 100 / 1550.

| Uji | Kondisi Input / Potensio | `adc_raw` (0–4095) | `soil_mv_avg` (mV) | `soil_pct` (%) | Status Pompa |
|---|---|---|---|---|---|
| 1 | Ujung kering (~0%) | ≥ 3290 *(perkiraan)* | ≥ 2650 | 0 | ON |
| 2 | Agak kering (~30%) | 2710 *(perkiraan)* | 2185 | 30 | ON |
| 3 | Lembap ideal (~50%) | 2325 *(perkiraan)* | 1875 | 50 | ON (zona mati, status dipertahankan) |
| 4 | Basah cukup (~70%) | 1940 *(perkiraan)* | 1565 | 70 | OFF |
| 5 | Jenuh air (~100%) | ≤ 1365 *(perkiraan)* | ≤ 1100 | 100 | OFF |

Status pompa di atas berlaku bila potensiometer diputar dari kering ke basah. Jika diputar sebaliknya, uji 3 berstatus OFF. Perbedaan ini adalah ciri histeresis: status di zona mati bergantung pada arah datangnya nilai.

### 3.2 Tabel 3.2 — Ambang Tunggal vs Histeresis (Uji Derau 30 Detik)

| Skema Algoritma Kendali | Jumlah Klik Relai (`relay_switches`) | Analisis Dampak terhadap Umur Relai & Beban Jaringan MQTT |
|---|---|---|
| Mode 0: Ambang Tunggal (45%) | ........ (perkiraan 10–30 klik) | Relai berpindah setiap kali nilai melintasi 45%. Dengan baca tiap 1 detik, batas atasnya 30 klik dalam 30 detik, dan setiap klik menjadi satu pesan perubahan status. |
| Mode 1: Histeresis (35%–60%) | ........ (perkiraan 0–1 klik) | Goyangan di 44–46% berada di zona mati sehingga relai diam. Di sekitar 35% relai hanya menyala sekali dan baru mati setelah lengas mencapai 60%. |

### 3.3 Pertanyaan Analisis C1–C6

> **[C1 – Mengingat]** Mengapa pin `GPIO 34` pada ESP32 dikonfigurasi hanya dengan `pinMode(34, INPUT)` dan tidak boleh menggunakan `INPUT_PULLUP` maupun dijadikan pin keluaran relai?

GPIO 34 sampai 39 adalah pin **input saja**. Pin ini tidak memiliki rangkaian penggerak keluaran dan tidak memiliki resistor *pull-up* atau *pull-down* internal, sehingga `INPUT_PULLUP` tidak berpengaruh dan `digitalWrite()` tidak menghasilkan tegangan. Karena termasuk ADC1, pin ini justru tepat untuk sensor analog yang harus tetap terbaca saat Wi-Fi aktif. Relai memerlukan pin dengan penggerak keluaran, misalnya GPIO 26.

> **[C2 – Memahami]** Jelaskan perbedaan nilai ukur antara `analogRead(34)` dan `analogReadMilliVolts(34)`! Mengapa kurva ADC mentah ESP32 memiliki deviasi nonlinear di bawah 150 mV dan di atas 2450 mV?

`analogRead()` mengembalikan cacah mentah 0–4095 tanpa koreksi. `analogReadMilliVolts()` mengembalikan tegangan dalam milivolt yang sudah dikoreksi dengan data kalibrasi pabrik di *eFuse* masing-masing keping. Di bawah sekitar 150 mV, rangkaian ADC belum merespons sehingga tegangan kecil terbaca nol. Di atas sekitar 2450 mV pada atenuasi 11 dB, penguat internal mendekati jenuh dan kurvanya melandai. Karena itu cacah mentah tidak bisa langsung dikalikan 3300/4095, dan kalibrasi sensor sebaiknya memakai nilai milivolt.

> **[C3 – Menerapkan]** Hitunglah nilai *duty cycle* PWM (skala 0–255 dan voltase efektif dari 3,3 V) ketika suhu DHT22 terbaca 31,5 °C dan 35,2 °C! Bandingkan dengan `fan_pwm_pct` di Serial Monitor!

Kode memakai `duty = map(suhu × 10, 280, 380, 0, 255)`. Fungsi `map()` Arduino memakai pembagian bilangan bulat sehingga hasilnya dibulatkan ke bawah.

| Suhu | Perhitungan | Duty (0–255) | `fan_pwm_pct` | V<sub>eff</sub> = duty/255 × 3,3 V | Hasil Serial Monitor |
|---|---|---|---|---|---|
| 31,5 °C | (315 − 280) × 255 / 100 = 89,25 | 89 | 34,9% | 1,15 V | ........ |
| 35,2 °C | (352 − 280) × 255 / 100 = 183,6 | 183 | 71,8% | 2,37 V | ........ |

> **[C4 – Menganalisis]** Analisislah cara kerja `bacaSoilMilliVoltsTerfilter()`! Apa kompromi yang terjadi apabila `UKURAN_FILTER` diperbesar dari N = 5 menjadi N = 60 sampel pada interval baca 1000 ms?

Fungsi ini menyimpan lima pembacaan terakhir dalam *ring buffer*. Setiap pemanggilan menimpa elemen tertua lalu mengembalikan rata-ratanya. Sebelum buffer penuh, rata-rata hanya dihitung dari sampel yang sudah ada sehingga pembacaan awal tidak tertarik ke nol (Listing 1).

Jika N dinaikkan menjadi 60, derau acak teredam sekitar √(60/5) ≈ 3,5 kali lebih baik. Kerugiannya, sistem menjadi lambat: perubahan mendadak baru terlihat penuh setelah 60 detik dan rata-rata tertinggal sekitar 30 detik, sehingga pompa terlambat menyala atau mati. Pemakaian RAM naik dari 20 menjadi 240 byte, angka yang masih kecil untuk ESP32.

> **[C5 – Mengevaluasi]** Berdasarkan Tabel 3.2, evaluasilah dampak logika tanpa histeresis terhadap kuota pesan *cloud* dan kontak relai pompa 220 V AC! Berapa lebar celah histeresis yang paling optimal untuk media tanah?

Ambang tunggal dapat menghasilkan puluhan klik dalam 30 detik. Pemutusan beban induktif menimbulkan percikan di kontak relai. Relai murah umumnya bertahan sekitar 10<sup>5</sup> siklus pada beban penuh, sehingga dengan satu klik per detik umurnya habis kurang dari dua hari. Setiap klik juga menjadi satu pesan perubahan status, menghasilkan puluhan ribu pesan tak berguna per hari, dan motor pompa cepat panas karena arus awal yang berulang.

Menurut kelompok kami, celah sekitar **20–25 poin** (misalnya 35%–60%) paling tepat. Celah ini jauh lebih lebar daripada derau sensor setelah filter (±2–3 poin), tetapi tidak terlalu lebar sehingga tanah tidak sempat terlalu kering sebelum pompa menyala.

> **[C6 – Mencipta]** Tambahkan fitur *Pump Run-Time Safety Cut-Off*: bila pompa menyala terus lebih dari 15 detik tetapi `soil_pct` tidak naik, pompa dimatikan otomatis, status dikunci `"fault": "DRY_RUN_PROTECTION"`, dan peringatan berkedip menyala.

```
// saat pompa baru menyala: catat waktu dan lengas awal
if (statusPompa && !pompaSebelum) {
  sejakPompaNyala = sekarang;
  soilSaatPompaNyala = soilPct;
}
// pompa nyala > 15 detik, tetapi lengas naik kurang dari 2 poin
if (statusPompa && sekarang - sejakPompaNyala > BATAS_JALAN_POMPA_MS &&
    soilPct - soilSaatPompaNyala < KENAIKAN_MINIMUM_PCT) {
  statusPompa = false;
  faultDryRun = true;          // JSON: "fault":"DRY_RUN_PROTECTION"
}
// di awal loop(): LED GPIO 2 berkedip 4 Hz selama fault aktif
digitalWrite(PIN_LED_FAULT, faultDryRun && ((sekarang / 125) % 2));
```
Listing 2: Logika pengaman pompa kering (*Dry-Run Safety Cut-Off*)

Perilaku fitur:

- Selama fault aktif, pompa dipaksa mati termasuk saat mode *override* manual.
- Fault terkunci sampai tombol GPIO 15 ditekan. Penekanan itu hanya mereset fault, sehingga operator wajib memeriksa tandon atau selang sebelum pompa menyala lagi.
- Batas kenaikan 2 poin dipakai agar derau kecil tidak dianggap tanah sudah basah.

Cara uji: putar potensiometer ke kering hingga pompa ON, lalu biarkan tidak berubah. Setelah 15 detik muncul `{"event":"fault","fault":"DRY_RUN_PROTECTION",...}`, relai mati, dan LED berkedip. Tangkapan layar bukti dilampirkan pada bagian lampiran.

### 3.4 Ceklis Verifikasi Laboratorium

| No | Unjuk Kerja yang Diverifikasi Asisten Laboratorium | Status | Paraf Asisten |
|---|---|---|---|
| 1 | Rangkaian terhubung pada pin aman (GPIO 34, 4, 15, 18, 26) dan terkompilasi tanpa galat | ☑ Lulus (kompilasi kedua mode) | |
| 2 | Pembacaan tanah terfilter dan pemetaan terbalik 0%–100% akurat | ☐ Lulus | |
| 3 | Demonstrasi *chattering* vs histeresis relai dan modulasi PWM kipas | ☐ Lulus | |
| 4 | Fitur C6 berfungsi, kode dan laporan telah di-*push* ke cabang Git kelompok | ☐ Lulus | |

**Lampiran:** tangkapan layar Serial Monitor Eksperimen 1–3 dan bukti fitur C6 (ditempel setelah pengujian).
