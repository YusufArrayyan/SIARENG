# Laporan Praktikum Lab-1 (Minggu 2): GPIO, ADC1, PWM, DHT22, dan Soil Moisture

Proyek: SIARENG (Siaga Lereng)
Kode: [`labs/minggu-02/`](../labs/minggu-02/)
Branch yang disarankan panduan: `feat/lab01-sensor-actuator`

> Angka di tabel pengamatan yang bertanda *(perkiraan)* dihitung dari kode dan rumus, belum diukur. Ganti dengan hasil Wokwi atau papan fisik sebelum dikumpulkan.

## Ringkasan pekerjaan

| Eksperimen | Hasil |
|---|---|
| Rangkaian | `diagram.json` sesuai Listing 1: DHT22 di GPIO 4, potensiometer (pengganti sensor tanah) di GPIO 34, tombol di GPIO 15, relai + LED hijau di GPIO 26, LED biru PWM di GPIO 18. Semua pin di luar ADC2 untuk input analog dan bukan GPIO 12. |
| 1. Karakterisasi ADC1 | `analogReadMilliVolts()` + *moving average* N = 5 + pemetaan terbalik 2650 mV (0%) sampai 1100 mV (100%). |
| 2. Histeresis relai | Sakelar `GUNAKAN_HISTERESIS` (0 = ambang tunggal 45%, 1 = histeresis 35%–60%). Kedua mode dikompilasi tanpa galat. |
| 3. PWM dan JSON | Kipas proporsional suhu 28–38 °C lewat `LEDC` 5 kHz 8 bit, tombol *override*, telemetri JSON per detik. |
| C6 | Pengaman pompa kering (*Dry-Run Safety Cut-Off*), lihat bagian C6. |

## Tabel 3.1: karakterisasi ADC1 (GPIO 34) dan pemetaan kelembapan tanah

Karena pemetaannya terbalik, potensiometer harus diputar ke tegangan **tinggi** untuk kondisi kering. Tegangan target per baris dihitung dari `soil_pct = (2650 − mV) × 100 / 1550`.

| Uji | Kondisi | `adc_raw` (0–4095) | `soil_mv_avg` (mV) | `soil_pct` (%) | Status pompa (histeresis, diputar dari kering ke basah) |
|---|---|---|---|---|---|
| 1 | Ujung kering (~0%) | *(perkiraan ≥ 3290)* | ≥ 2650 | 0 | ON (< 35%) |
| 2 | Agak kering (~30%) | *(perkiraan 2710)* | 2185 | 30 | ON (< 35%) |
| 3 | Lembap ideal (~50%) | *(perkiraan 2325)* | 1875 | 50 | ON (zona mati 35–60%, status dipertahankan) |
| 4 | Basah cukup (~70%) | *(perkiraan 1940)* | 1565 | 70 | OFF (≥ 60%) |
| 5 | Jenuh air (~100%) | *(perkiraan ≤ 1365)* | ≤ 1100 | 100 | OFF |

`adc_raw` perkiraan memakai hubungan linear ideal `D = mV / 3300 × 4095`. Pada ESP32 asli angkanya akan menyimpang, terutama di bawah 150 mV dan di atas 2450 mV (lihat C2).
Bila potensiometer diputar ke arah sebaliknya (dari basah ke kering), uji 3 akan berstatus **OFF**. Itulah ciri histeresis: status di zona mati bergantung pada arah datangnya.

## Tabel 3.2: ambang tunggal vs histeresis (uji derau 30 detik)

| Skema | `relay_switches` | Analisis |
|---|---|---|
| Mode 0: ambang tunggal 45% | *(isi; perkiraan 10–30 klik bila knop digoyang di 44–46%)* | Setiap kali nilai melintasi 45%, relai berpindah. Dengan pembacaan tiap 1 detik, batas atasnya 30 klik dalam 30 detik. Setiap klik juga berarti satu pesan perubahan status bila nanti dikirim lewat MQTT. |
| Mode 1: histeresis 35–60% | *(isi; perkiraan 0 klik di zona 44–46%, paling banyak 1 klik di sekitar 35%)* | Goyangan di 44–46% berada di dalam zona mati, jadi relai tidak berubah. Di sekitar 35% relai hanya menyala sekali dan baru mati setelah lengas mencapai 60%. |

## 3.2 Jawaban analisis

### C1. Mengapa GPIO 34 hanya `INPUT`

GPIO 34–39 di ESP32 adalah pin **input saja**. Bagian penggerak keluaran (*output driver*) dan resistor *pull-up/pull-down* internal memang tidak ada di pin ini, jadi `INPUT_PULLUP` tidak berpengaruh dan `digitalWrite` tidak menghasilkan tegangan. Pin ini justru ideal untuk sensor analog karena termasuk ADC1 dan tetap bisa dibaca saat Wi-Fi aktif. Relai harus memakai pin yang punya penggerak keluaran, misalnya GPIO 26.

### C2. `analogRead(34)` vs `analogReadMilliVolts(34)`

- `analogRead()` mengembalikan angka mentah 0–4095 tanpa koreksi.
- `analogReadMilliVolts()` mengembalikan tegangan dalam mV yang sudah dikoreksi memakai data kalibrasi pabrik di *eFuse* tiap keping ESP32.

ADC ESP32 tidak linear di ujung-ujungnya. Di bawah ~150 mV, rangkaian ADC belum merespons, sehingga semua tegangan kecil terbaca 0. Di atas ~2450 mV (pada atenuasi 11 dB), penguat internal mulai jenuh dan kurvanya melandai. Karena itu angka mentah tidak bisa langsung dikalikan 3300/4095, dan `analogReadMilliVolts()` lebih tepat untuk kalibrasi.

### C3. Duty cycle PWM

Rumus di kode: `duty = map(suhu × 10, 280, 380, 0, 255)`. Fungsi `map()` Arduino memakai pembagian bilangan bulat, jadi hasilnya dibulatkan ke bawah.

| Suhu | Hitungan | Duty (0–255) | Persen | V<sub>eff</sub> = duty/255 × 3,3 V |
|---|---|---|---|---|
| 31,5 °C | (315 − 280) × 255 / 100 = 89,25 | 89 | 34,9% | 1,15 V |
| 35,2 °C | (352 − 280) × 255 / 100 = 183,6 | 183 | 71,8% | 2,37 V |

`fan_pwm_pct` di Serial Monitor seharusnya menampilkan 34,9 dan 71,8. Isi kolom pembanding dengan hasil pengamatanmu.

### C4. Cara kerja `bacaSoilMilliVoltsTerfilter()` dan *trade-off* N

Fungsi ini menyimpan 5 pembacaan terakhir dalam *ring buffer*. Setiap pemanggilan menimpa elemen tertua, lalu mengembalikan rata-ratanya. Sebelum buffer penuh, rata-rata hanya dihitung dari sampel yang sudah ada, supaya pembacaan awal tidak tertarik ke nol.

Jika N dinaikkan dari 5 menjadi 60 dengan interval 1 detik:

- **Keuntungan:** derau jauh lebih teredam. Standar deviasi derau acak turun kira-kira √(60/5) ≈ 3,5 kali lipat.
- **Kerugian:** sistem jadi lambat. Perubahan mendadak baru terlihat penuh setelah 60 detik, dan rata-rata 1 menit tertinggal sekitar 30 detik. Pompa terlambat menyala atau mati, dan tanah bisa sudah kebanjiran sebelum filter "percaya" tanahnya basah.
- Pemakaian RAM naik dari 20 menjadi 240 byte. Ini kecil untuk ESP32.

### C5. Dampak tanpa histeresis

Berdasarkan Tabel 3.2, ambang tunggal bisa menghasilkan puluhan klik dalam 30 detik. Kalau berlangsung sepanjang hari di kebun kopi:

- **Relai pompa 220 V AC:** setiap pemutusan beban induktif menimbulkan percikan api (*arcing*) di kontak. Relai murah umumnya bertahan sekitar 10<sup>5</sup> siklus pada beban penuh. Dengan 1 klik per detik, umur itu habis dalam kurang dari 2 hari.
- **Kuota cloud:** 1 pesan per perubahan status berarti puluhan ribu pesan per hari yang tidak berguna, sehingga beban broker dan biaya kuota ikut naik.
- **Pompa:** motor yang terus dinyalakan dan dimatikan cepat panas karena arus awal (*inrush current*).

Celah histeresis yang menurut kami paling cocok untuk media tanah adalah **sekitar 20–25 poin**, misalnya 35%–60% seperti di panduan. Celah ini harus jauh lebih lebar dari derau sensor (biasanya ±2–3 poin setelah filter), tetapi cukup sempit agar tanah tidak terlalu kering sebelum pompa menyala. Pengujian di media tanam sebenarnya tetap diperlukan.

### C6. Pengaman waktu jalan maksimum pompa

Sudah diterapkan di [`labs/minggu-02/src/main.cpp`](../labs/minggu-02/src/main.cpp):

```cpp
// saat pompa baru menyala: catat waktu dan lengas awal
if (statusPompa && !pompaSebelum) { sejakPompaNyala = sekarang; soilSaatPompaNyala = soilPct; }

// pompa nyala > 15 detik, tetapi lengas naik kurang dari 2 poin -> matikan dan kunci
if (statusPompa && sekarang - sejakPompaNyala > 15000 &&
    soilPct - soilSaatPompaNyala < 2.0f) {
  statusPompa = false;
  faultDryRun = true;     // JSON menampilkan "fault":"DRY_RUN_PROTECTION"
}
```

Perilakunya:

- Selama `faultDryRun` aktif, pompa dipaksa mati, termasuk saat mode *override* manual, dan LED di GPIO 2 berkedip 4 Hz.
- Fault **terkunci** sampai tombol GPIO 15 ditekan. Penekanan itu hanya mereset fault, tidak mengganti mode. Dengan begitu operator harus memeriksa tandon atau selang sebelum pompa boleh menyala lagi.
- Batas 2 poin dipakai supaya sedikit derau tidak dianggap "tanah sudah basah".

**Cara menguji di Wokwi:** putar potensiometer ke kering (pompa ON), lalu biarkan tidak berubah. Setelah 15 detik muncul `{"event":"fault","fault":"DRY_RUN_PROTECTION",...}`, relai mati, dan LED berkedip. Tekan tombol kuning untuk mereset. Lampirkan tangkapan layarnya di laporan.

## 3.3 Ceklis verifikasi

| No | Unjuk kerja | Status |
|---|---|---|
| 1 | Rangkaian di pin aman dan terkompilasi tanpa galat | Lulus (kompilasi PlatformIO, kedua mode) |
| 2 | Pembacaan tanah terfilter dan pemetaan terbalik 0–100% | Perlu didemonstrasikan di Wokwi |
| 3 | Demonstrasi *chattering* vs histeresis dan PWM kipas | Perlu didemonstrasikan di Wokwi |
| 4 | Fitur C6 berfungsi, kode dan laporan di-*push* | Kode sudah ada. Tangkapan layar bukti perlu ditambahkan |
