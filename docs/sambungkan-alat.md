# Hari barang datang: sambungkan SIARENG

Panduan ini khusus untuk komponen yang dibeli di Shopee (lihat `docs/Daftar_Belanja_Shopee_SIARENG.xlsx`).
Firmware sudah disiapkan untuk komponen tersebut, jadi **tidak ada kode yang perlu diubah**. Cukup rakit, upload, lalu kalibrasi lewat Serial Monitor.

Perkiraan waktu: 1 jam di meja, ditambah 1–2 jam untuk pemasangan di box.

## 0. Cek isi paket

| Barang | Jumlah | Catatan |
|---|---|---|
| ESP32 30 pin CP2102 Type C | 1 | Label pin tercetak di papan (D21, D22, 3V3, GND, ...) |
| Kabel USB-A ke Type C | 1 | Untuk upload dan daya |
| MPU-6050 GY-521 | 1 | Header pin biasanya belum disolder |
| Sensor tanah kapasitif HW-390 | 1–2 | Satu cadangan bila beli 2 |
| Sensor hujan (panel + modul biru) | 1 | |
| Buzzer aktif TMB12A05 | 1 | Kaki panjang atau tanda **+** = positif |
| LED merah, kuning, hijau | 1 pak per warna | Kaki panjang = anoda (+) |
| Resistor 200 Ω (merah-hitam-cokelat) | 1 pak | Perlu 3 |
| Tombol tactile 12×12 | 1 pak | Perlu 1 |
| Breadboard mini SYB-170 | 3 | Bisa disambung lewat tonjolan di sisi papan |
| Kabel jumper M-M dan M-F | 2 set | |
| Header female 1×40 | 1 | Untuk versi PCB lubang |
| PCB lubang 9×15, box IP65, cable gland PG7 ×3, kabel 4 jalur 5 m | | Untuk pemasangan di lapangan (bagian 6) |

Bila header MPU-6050 belum terpasang, solder dulu 8 pin header male bawaan modul. Tanpa solder, sambungan I2C goyang dan sensor sering "terputus".

## 1. Pasang driver dan siapkan laptop (sekali saja)

1. Pasang driver **CP210x** dari situs Silicon Labs ("CP210x USB to UART Bridge VCP Drivers"). Windows 11 biasanya memasangnya otomatis.
2. Colokkan ESP32. Di **Device Manager → Ports (COM & LPT)** harus muncul `Silicon Labs CP210x ... (COMx)`.
   Bila tidak muncul, kabelnya mungkin kabel daya saja. Coba kabel lain atau port USB lain.
3. VS Code + ekstensi PlatformIO sudah terpasang dari langkah simulasi (lihat `panduan-pemula.md`).

## 2. Susun breadboard

Breadboard mini tidak punya jalur daya merah/biru, dan ESP32 terlalu lebar untuk satu papan. Susunannya:

```
  [ papan A ][ papan B ]      <- disambung berdampingan; ESP32 melintang di atas keduanya
       ESP32 30 pin           (deretan pin kiri di papan A, deretan pin kanan di papan B)

  [ papan C ]                 <- jalur daya: 2 kolom untuk 3V3, 2 kolom untuk GND,
                                 sisanya untuk LED, resistor, buzzer, tombol
```

- Setiap kolom berisi 5 lubang yang terhubung. Di papan C, pakai dua kolom bersebelahan untuk **3V3** (jembatani dengan jumper) dan dua kolom untuk **GND**. Hasilnya 8–9 lubang per jalur, cukup untuk semua modul.
- Tarik satu jumper dari pin `3V3` ESP32 ke jalur 3V3 papan C, dan satu dari pin `GND` ke jalur GND.
- **Semua sensor diberi daya 3V3, jangan VIN atau 5V.** ADC ESP32 hanya tahan sampai 3,3 V.

## 3. Sambungan kabel

| Komponen | Pin komponen | Ke ESP32 / papan C |
|---|---|---|
| MPU-6050 | VCC, GND | jalur 3V3, jalur GND |
| | SCL, SDA | **D22**, **D21** |
| Sensor tanah HW-390 | VCC, GND | jalur 3V3, jalur GND |
| | AOUT | **D34** |
| Modul sensor hujan | VCC, GND | jalur 3V3, jalur GND |
| | **AO** (bukan DO) | **D35** |
| | 2 pin sisi lain | ke panel hujan (kabel bawaan) |
| Buzzer aktif | + (kaki panjang) | **D25** |
| | – | jalur GND |
| LED hijau | kaki panjang | resistor 200 Ω → **D26** |
| LED kuning | kaki panjang | resistor 200 Ω → **D27** |
| LED merah | kaki panjang | resistor 200 Ω → **D14** |
| Ketiga LED | kaki pendek | jalur GND |
| Tombol | satu kaki | **D15** |
| | kaki diagonalnya | jalur GND |

Kabel M-F dipakai dari pin modul (MPU, sensor tanah, modul hujan) ke breadboard. Kabel M-M dipakai antar-lubang breadboard.

Buzzer aktif 5 V di pin 3,3 V tetap berbunyi, hanya lebih pelan. Itu cukup untuk uji dan untuk di dalam box.

## 4. Upload firmware

Buka folder `firmware/` di VS Code. Pilih target **`env:alat`** di status bar PlatformIO (bawah), lalu klik **Upload**. Lewat terminal:

```
pio run -e alat -t upload
pio device monitor
```

Bila upload berhenti di `Connecting.....`, tahan tombol **BOOT** di ESP32 sampai persentase upload muncul.

Target `alat` sudah mengatur mode sensor asli dan buzzer aktif. Jangan pakai target `esp32doit-devkit-v1`, yang masih untuk simulasi potensiometer.

## 5. Uji dan kalibrasi lewat Serial Monitor

Saat menyala, ESP32 menguji perakitan: **LED hijau → kuning → merah menyala bergantian, lalu buzzer bip sekali**. Bila ada yang tidak menyala, cek arah kaki LED/buzzer dan pin GPIO-nya.

Di Serial Monitor, ketik perintah lalu tekan Enter:

| Ketik | Fungsi |
|---|---|
| `info` | Menampilkan nilai RAW sensor, kalibrasi tersimpan, dan apakah MPU-6050 terbaca |
| `tes` | Ulangi uji LED dan buzzer |
| `kal tanah kering` | Simpan nilai saat probe tanah **di udara** |
| `kal tanah basah` | Simpan nilai saat probe dicelup **segelas air** sampai garis batas (jangan sampai bagian elektronik basah) |
| `kal hujan kering` | Simpan nilai saat panel hujan kering |
| `kal hujan basah` | Simpan nilai saat panel hujan **dibasahi merata** |
| `nol` | Jadikan posisi MPU-6050 sekarang sebagai patokan (sama dengan menekan tombol) |
| `kal reset` | Hapus kalibrasi, kembali ke nilai bawaan |

Kalibrasi tersimpan di memori ESP32, jadi tidak hilang saat dicabut atau di-upload ulang.

**Uji lolos jika:**

- [ ] `info` menunjukkan `"mpu_ok":true`. Bila `false`, cek SDA/SCL tertukar atau VCC belum ke 3V3. Setelah kabel dibetulkan, firmware menyambung ulang sendiri dalam 5 detik.
- [ ] Setelah empat perintah `kal`, telemetri menunjukkan `soil_pct` mendekati 0 saat probe di udara dan mendekati 100 saat dicelup air. `rain_pct` juga begitu untuk panel hujan.
- [ ] Breadboard dimiringkan pelan, `tilt_delta_deg` naik. Lebih dari 2° → LED kuning, lebih dari 5° bersama tanah basah → LED merah berkedip dan buzzer berbunyi.
- [ ] Bila muncul `"event":"peringatan"` soal selisih RAW, kabel AO kemungkinan lepas atau tertancap di pin DO.

Bila MPU-6050 belum terpasang atau rusak, alat tetap memantau tanah dan hujan. Dashboard menampilkan pesan galat MPU.

## 6. Tampilkan di dashboard

**Lewat USB (paling mudah):** tutup Serial Monitor, lalu klik ganda `backend-api/jalankan.bat`.
Skrip ini menyiapkan Python (sekali saja), mencari port ESP32 sendiri, dan membuka `http://localhost:8000`.

**Lewat WiFi (alat jauh dari laptop):**

1. Salin `firmware/include/secrets.example.h` menjadi `secrets.h` (sudah ada bila pernah dibuat). Isi nama dan sandi WiFi **2,4 GHz**, serta `SERVER_URL` dengan IP laptop yang ditampilkan `jalankan.bat`.
2. Upload target **`alat-wifi`**: `pio run -e alat-wifi -t upload`.
3. Jalankan `jalankan.bat`, pilih **Allow access** saat Windows bertanya soal firewall.
4. ESP32 cukup diberi daya dari charger HP 5 V. Data muncul di dashboard bila laptop dan ESP32 di WiFi yang sama.

## 7. Pindah ke PCB dan box IP65 (pemasangan di lapangan)

Lakukan setelah semua uji di bagian 5 lolos.

1. **PCB lubang:** potong header female menjadi dua batang 15 pin, solder di PCB dengan jarak sama seperti pin ESP32, lalu tancapkan ESP32 di atasnya. Solder resistor, LED, buzzer, dan tombol mengikuti tabel bagian 3. Modul MPU-6050 dan modul biru sensor hujan juga ditaruh di PCB (pakai sisa header female).
2. **MPU-6050 harus kaku terhadap box.** Kencangkan PCB ke dasar box dengan baut atau lem tembak. Pergeseran PCB di dalam box terbaca sebagai pergeseran lereng.
3. **Bor box:** tiga lubang 12,5 mm di sisi bawah box (menghadap tanah, supaya air tidak masuk dari atas).
   - Gland 1: kabel sensor tanah.
   - Gland 2: kabel panel hujan.
   - Lubang 3: kabel USB daya. Steker USB tidak muat lewat gland, jadi masukkan steker lewat lubang, colokkan, lalu tutup celah dengan lem tembak atau silikon. Gland ketiga jadi cadangan.
4. **Kabel 4 jalur 5 m:** potong ±3 m untuk sensor tanah dan ±2 m untuk panel hujan.
   - Sensor tanah: 3 inti untuk VCC, GND, AOUT. Catat warnanya, misalnya merah = VCC, hitam = GND, kuning = AOUT. Inti keempat cadangan.
   - Panel hujan: 2 inti dari panel ke modul biru di dalam box. **Modul biru tetap di dalam box**, hanya panelnya yang di luar.
5. **Lindungi sensor tanah:** bagian elektronik di ujung atas HW-390 dibungkus heat shrink atau dilapisi lem tembak/cat kuku bening. Hanya batang probe di bawah garis putih yang boleh masuk tanah.
6. **LED:** bor 3 lubang 5 mm di tutup box agar LED terlihat dari luar, lalu tutup celahnya dengan lem tembak.
7. Kencangkan mur gland sampai karet menjepit kabel. Tarik kabel pelan untuk memastikan tidak bergeser.
8. **Di lokasi:** tancapkan box pada patok yang ditanam kuat di lereng. Tunggu 1 menit setelah alat menyala, lalu tekan tombol (atau ketik `nol`). Posisi itulah patokan kemiringan.
9. Ulangi `kal tanah kering`/`kal tanah basah` di tanah lokasi bila memungkinkan, karena tiap jenis tanah memberi nilai berbeda.

Langkah pemasangan yang lebih lengkap (lokasi patok, catu daya surya untuk versi lanjutan) ada di `docs/panduan-perakitan.md`.

## Masalah umum

| Gejala | Penyebab dan solusi |
|---|---|
| Port COM tidak muncul | Kabel hanya untuk daya, atau driver CP210x belum terpasang |
| Upload gagal `Failed to connect` | Tahan tombol BOOT saat `Connecting...`. Tutup Serial Monitor dan `jalankan.bat` dulu, karena port hanya bisa dipakai satu program |
| LED kuning terus, tidak ada telemetri | Sedang mengukur patokan (2 detik). Bila lebih lama, cek pesan MPU di Serial Monitor |
| `soil_raw` selalu 0 atau 4095 | AOUT tidak tersambung ke D34, atau VCC sensor belum ke 3V3 |
| `rain_pct` tidak berubah | Kabel ke **DO**, bukan **AO** |
| Buzzer tidak bunyi | Kaki + dan – terbalik |
| `jalankan.bat` menulis "ESP32 belum tercolok" | Colokkan ESP32. Bila sudah, tutup Serial Monitor PlatformIO |
| Dashboard kosong lewat WiFi | `SERVER_URL` salah IP, WiFi 5 GHz, atau firewall Windows memblokir port 8000 |
