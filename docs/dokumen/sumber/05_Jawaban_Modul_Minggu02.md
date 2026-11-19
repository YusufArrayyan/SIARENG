---
berkas: Jawaban_Modul_Minggu02_SIARENG
jenis: LEMBAR JAWABAN
unit: PRODI S1 | INFORMATIKA | Jurusan Teknik Informatika | Fakultas Teknik UNIB
judul: LEMBAR JAWABAN MINGGU KE-2
subjudul: Matriks Keputusan Berbobot & Problem Set Perangkat Keras
kolom: Minggu=2 dari 16 | Kelompok=SIARENG | Sub-CPMK=Sub-CPMK 1.2
kepala_kiri: Lembar Jawaban Minggu 2 — Teknologi IoT
kepala_kanan: Modul 1: Pemilihan Perangkat Keras & Konektivitas IoT
kaki: Kelompok SIARENG · Kurikulum OBE — Standar SN-Dikti & LAM Infokom
---

> **Capaian Pembelajaran Minggu Ke-2 (Sub-CPMK 1.2 — Level C4)**
> Mahasiswa mampu menganalisis dan menjustifikasi pemilihan sensor, aktuator, platform MCU/SBC, dan teknologi konektivitas menggunakan matriks keputusan berbobot (*Weighted Decision Matrix*).
> Dokumen ini memuat **Lembar Kerja Terstruktur Minggu 2** (WDM dan draf BoM Kasus B) dan **jawaban Problem Set Minggu 2** level C1–C6. Soal C6 dikerjakan untuk proyek SIARENG sebagai bahan Proposal Milestone 1.

| No | Peran Rekayasa | Nama Anggota | NPM |
|---|---|---|---|
| 1 | Device & Firmware Engineer | ........................................ | .................... |
| 2 | Back-End & Data Engineer | ........................................ | .................... |
| 3 | Security & DevOps Engineer | ........................................ | .................... |
| 4 | Dashboard Engineer & Project Manager | ........................................ | .................... |

## Bagian 1 — Lembar Kerja Terstruktur: Matriks Keputusan & Draf BoM

> **Studi Kasus B: Smart Farming Kebun Kopi Robusta Rejang Lebong.** Enam blok kebun berjarak 150–850 m dari pondok tanpa listrik PLN, dua blok lembah *blank spot* seluler, satu *greenhouse* 25 m dari pondok dengan katup solenoida 12 V dan kipas kabut. Listrik dan internet hanya di pondok. Plafon BoM Rp4.500.000, biaya bulanan minimal, perawatan baterai paling sering enam bulan sekali.

**Kandidat arsitektur.** Opsi 1: *Full Wi-Fi Extender* (ESP32 Wi-Fi tiap blok dan *repeater* jarak jauh). Opsi 2: ESP32 + modem seluler per blok langsung ke *cloud*. Opsi 3: hibrida ESP32 + LoRa SX1276 (920–923 MHz) di kebun, ESP32 Wi-Fi di *greenhouse*, dan Raspberry Pi *gateway* di pondok.

| Kriteria Evaluasi (C<sub>i</sub>) | Bobot (w<sub>i</sub>) | Opsi 1: Wi-Fi Extender | Opsi 2: ESP32 + SIM | Opsi 3: Hibrida LoRa | Alasan Teknis & Rujukan Datasheet |
|---|---|---|---|---|---|
| 1. Jangkauan & penetrasi kanopi kebun | 0,25 | r = 1 | r = 2 | r = 5 | Wi-Fi 2,4 GHz efektif 30–80 m dan teredam dedaunan; seluler gagal di dua blok lembah; LoRa sub-GHz 2–15 km |
| 2. Efisiensi daya & umur baterai/surya | 0,25 | r = 2 | r = 2 | r = 5 | Wi-Fi TX 80–240 mA dan proses sambung ulang lama; registrasi modem boros; LoRa TX singkat + *deep sleep* 10–150 µA |
| 3. Kecukupan I/O sensor, ADC, & komputasi | 0,15 | r = 5 | r = 4 | r = 4 | Ketiganya ESP32 (ADC1 12-bit, I2C); opsi 2 dan 3 memakai UART/SPI untuk modem atau radio |
| 4. Kematangan ekosistem *software* & keamanan | 0,15 | r = 5 | r = 4 | r = 3 | Wi-Fi dan seluler IP penuh (MQTT/TLS/OTA); LoRa non-IP, perlu *gateway* penerjemah dan enkripsi tingkat aplikasi |
| 5. Efisiensi biaya BoM (≤ Rp4,5 juta) & OPEX | 0,20 | r = 2 | r = 1 | r = 4 | Opsi 1 perlu *repeater* outdoor bertenaga surya; opsi 2 butuh 6 kartu SIM bulanan; opsi 3 tanpa biaya bulanan |
| **Total skor terboboti (S<sub>j</sub> = Σ w<sub>i</sub> r<sub>ij</sub>)** | **1,00** | **S<sub>1</sub> = 2,65** | **S<sub>2</sub> = 2,40** | **S<sub>3</sub> = 4,35** | **Keputusan: Opsi 3** |

Rincian perhitungan:

- S<sub>1</sub> = 0,25(1) + 0,25(2) + 0,15(5) + 0,15(5) + 0,20(2) = 0,25 + 0,50 + 0,75 + 0,75 + 0,40 = **2,65**
- S<sub>2</sub> = 0,25(2) + 0,25(2) + 0,15(4) + 0,15(4) + 0,20(1) = 0,50 + 0,50 + 0,60 + 0,60 + 0,20 = **2,40**
- S<sub>3</sub> = 0,25(5) + 0,25(5) + 0,15(4) + 0,15(3) + 0,20(4) = 1,25 + 1,25 + 0,60 + 0,45 + 0,80 = **4,35**

**Analisis sensitivitas.** Bila bobot jangkauan diturunkan menjadi 0,15 dan bobot ekosistem dinaikkan menjadi 0,25, skor menjadi S<sub>1</sub> = 3,05, S<sub>2</sub> = 2,60, dan S<sub>3</sub> = 4,15. Opsi 3 tetap unggul, sehingga keputusan tidak rapuh terhadap pergeseran bobot ±10%.

**Sensor lengas tanah dan catu daya.** Dipilih *Capacitive Soil Moisture Sensor v1.2* karena elektrodanya terisolasi sehingga tidak terkorosi seperti garpu resistif, dengan bagian elektronik di atas garis batas dilapisi epoksi. Simpul kebun memakai panel surya 6 V 5 W, dua baterai 18650 paralel (±6000 mAh), TP4056, dan regulator 3,3 V *low-dropout*, dengan ESP32 bangun 15 menit sekali.

| Bagian Sistem | Rincian Komponen per Unit | Harga per Unit (perkiraan) | Jumlah | Subtotal |
|---|---|---|---|---|
| Simpul kebun | ESP32 Rp82.000, LoRa SX1276 Ra-02 Rp75.000, sensor tanah kapasitif Rp12.000, DHT22 Rp24.000, BH1750 Rp20.000, panel surya 5 W Rp85.000, 2 × 18650 Rp100.000, TP4056 + LDO Rp18.000, box IP65 Rp45.000 | Rp461.000 | 6 | Rp2.766.000 |
| Simpul *greenhouse* | ESP32, sensor tanah, DHT22, BH1750, relai 2 kanal, katup solenoida 12 V, kipas kabut 12 V, adaptor 12 V | Rp405.000 | 1 | Rp405.000 |
| *Gateway* pondok | Raspberry Pi 4 2 GB set minimal Rp1.100.000 + LoRa SX1276 Rp75.000 | Rp1.175.000 | 1 | Rp1.175.000 |
| **Total BoM prototipe** | | | | **Rp4.346.000** |

Total berada di bawah plafon dengan sisa sekitar Rp154.000. Dengan satu modul SX1276 di *gateway*, komunikasi berupa LoRa titik-ke-titik, bukan LoRaWAN penuh; *gateway* LoRaWAN 8 kanal (SX1302) di atas Rp1,5 juta sehingga melewati plafon. Untuk enam simpul yang mengirim tiap 15 menit dengan jadwal acak, LoRa titik-ke-titik sudah memadai. Harga pada tabel ini merupakan perkiraan pasar daring dan perlu dicek ulang per toko.

## Bagian 2 — Jawaban Problem Set Minggu 2 (Level C1–C6)

> **Soal 1 [C1 – Remember]** (a) Sebutkan perbedaan sensor keluaran analog dan digital beserta dua contoh modulnya! (b) Daftarlah pin GPIO ESP32 blok ADC1 yang aman dipakai bersamaan dengan Wi-Fi! (c) Sebutkan lima teknologi konektivitas IoT dari jangkauan terpendek hingga terjauh!

| Jenis | Keluaran | Contoh Modul |
|---|---|---|
| Sensor analog | Tegangan kontinu, dibaca ADC mikrokontroler, perlu kalibrasi di firmware | Sensor tanah kapasitif v1.2, LDR, sensor gas MQ-2 |
| Sensor digital | Paket bit lewat bus (I2C, satu kabel, UART); ADC dan kalibrasi ada di dalam sensor | DHT22, BME280, HC-SR04, PZEM-004T |

(b) Pin ADC1 ESP32: **GPIO 32, 33, 34, 35, 36 (VP), dan 39 (VN)**; GPIO 34–39 hanya dapat menjadi input.
(c) Urutan jangkauan: Zigbee/Thread (10–30 m per lompatan), BLE 5.x (10–50 m), Wi-Fi (30–80 m), NB-IoT/LTE-M (1–10 km mengikuti BTS), LoRa/LoRaWAN (2–15 km).

> **Soal 2 [C2 – Understand]** (a) Mengapa Raspberry Pi 4/5 yang jauh lebih cepat justru tidak tepat dijadikan simpul sensor tanah bertenaga panel surya kecil di tengah kebun? (b) Mengapa LoRaWAN melarang *payload* teks JSON panjang dan menuntut format biner ringkas?

(a) Raspberry Pi menarik 2,7–3,5 W saat diam dan tidak memiliki mode *deep sleep* orde mikroampere. Kebutuhan hariannya 65–85 Wh, sementara panel 5 W hanya menghasilkan sekitar 15–20 Wh per hari. RPi juga tidak memiliki ADC bawaan dan kartu microSD-nya rentan rusak saat baterai habis mendadak. ESP32 dengan *deep sleep* hanya memerlukan beberapa mAh per hari, dan kecepatan prosesor RPi tidak dibutuhkan untuk membaca satu sensor tiap 15 menit.

(b) *Payload* LoRaWAN dibatasi 51–222 byte tergantung *spreading factor*, laju data hanya 0,3–27 kbps, dan pita ISM membatasi waktu siar (*duty cycle*). JSON boros karena nama kunci dan tanda kutip ikut terkirim: `{"soil_pct":45.2,"temp_c":27.1}` berukuran 32 byte, sedangkan versi biner cukup 4 byte (dua `int16` dikali 10). Paket panjang membuat radio menyala lebih lama, memperbesar peluang tabrakan, dan cepat menghabiskan kuota waktu siar, sehingga dipakai CBOR atau *byte packing*.

> **Soal 3 [C3 – Apply]** Sensor tekanan air analog mengeluarkan 0,5 V (0 bar) hingga 4,5 V (10 bar) dengan pembagi tegangan R<sub>1</sub> = 10 kΩ (seri) dan R<sub>2</sub> = 20 kΩ (ke GND). Hitunglah (a) rentang tegangan ke pin ESP32, (b) cacah ADC saat 6,0 bar, (c) umur baterai LiFePO4 4000 mAh (η = 0,80) bila ESP32 aktif 2,5 detik (140 mA) tiap 10 menit dan tidur 80 µA!

| Besaran | Perhitungan | Hasil |
|---|---|---|
| Faktor pembagi | V<sub>out</sub> = V<sub>in</sub> × R<sub>2</sub>/(R<sub>1</sub> + R<sub>2</sub>) = V<sub>in</sub> × 20/30 | 0,667 × V<sub>in</sub> |
| (a) Rentang tegangan | 0,5 × 0,667 sampai 4,5 × 0,667 | 0,333 V – 3,00 V (aman ≤ 3,3 V) |
| V<sub>in</sub> pada 6,0 bar | 0,5 + (4,0/10) × 6,0 | 2,90 V |
| V<sub>out</sub> pada 6,0 bar | 2,90 × 2/3 | 1,933 V |
| (b) Cacah ADC ideal | D = 1,933 / 3,3 × 4095 | ≈ 2399 |
| Arus rata-rata | I<sub>avg</sub> = (140 × 2,5 + 0,08 × 597,5) / 600 = (350 + 47,8) / 600 | 0,663 mA |
| (c) Umur baterai | T = 4000 × 0,80 / 0,663 | ≈ 4826 jam ≈ 201 hari |

> **Soal 4 [C4 – Analyze]** Bedahlah tiga kesalahan rekayasa pada prototipe penyiram tanaman (sensor tanah di GPIO 25, relai di GPIO 12, ambang tunggal 45%) beserta solusi perbaikannya!

| Kesalahan | Akar Masalah | Solusi Perbaikan |
|---|---|---|
| Pembacaan tanah kacau setelah `WiFi.begin()` | GPIO 25 termasuk ADC2 yang dipakai perangkat keras radio Wi-Fi, sehingga `analogRead()` gagal saat Wi-Fi aktif | Pindahkan sensor ke pin ADC1, misalnya GPIO 34, dan gunakan `analogReadMilliVolts()` |
| ESP32 sesekali gagal *boot* saat relai terpasang | GPIO 12 (MTDI) adalah pin *strapping* tegangan flash; relai yang menariknya HIGH saat *boot* membuat flash disetel 1,8 V | Pindahkan relai ke pin aman seperti GPIO 26; hindari GPIO 0, 2, 5, 12, 15 untuk beban yang menarik level saat *boot* |
| Relai bergetar belasan kali per menit | Ambang tunggal 45%: derau ±0,5% di sekitar ambang membuat kondisi bergantian (*chattering*) | Histeresis dua ambang (ON < 35%, OFF ≥ 60%, status dipertahankan di antaranya) ditambah *moving average* |

> **Soal 5 [C5 – Evaluate]** Susunlah matriks keputusan berbobot minimal 5 kriteria untuk pemantauan suhu kabin 25 truk pengangkut ikan dari Pulau Baai ke Curup dan Mukomuko dengan Kandidat A (Wi-Fi *hotspot* sopir), B (LoRaWAN 3 *gateway*), dan C (LTE-M/NB-IoT + buffer flash)!

| Kriteria | Bobot | A: Hotspot Sopir | B: LoRaWAN 3 Gateway | C: LTE-M + Buffer Flash |
|---|---|---|---|---|
| Cakupan sepanjang rute | 0,30 | 2 | 1 | 4 |
| Keandalan & keutuhan data | 0,25 | 1 | 2 | 5 |
| Latensi peringatan suhu | 0,15 | 3 | 2 | 4 |
| Biaya infrastruktur (CAPEX) | 0,15 | 5 | 2 | 3 |
| Biaya bulanan & pengelolaan (OPEX) | 0,15 | 3 | 4 | 3 |
| **Total** | **1,00** | **2,50** | **2,00** | **3,95** |

Rekomendasi kelompok: **Kandidat C**. Truk bergerak melintasi wilayah luas yang hanya terjangkau operator seluler, dan LTE-M/NB-IoT dirancang untuk aset bergerak dengan mode hemat daya PSM/eDRX. Celah sinyal di jalur pegunungan ditutup buffer flash lokal, sehingga data tetap tercatat dengan stempel waktu dan dikirim setelah sinyal kembali. Kandidat A gugur karena bergantung pada HP dan kuota sopir; kandidat B gugur karena tiga *gateway* tidak mencakup rute ratusan kilometer. Uji sensitivitas dengan bobot CAPEX 0,30 dan cakupan 0,15 menghasilkan A = 2,95, B = 2,15, C = 3,80, sehingga C tetap unggul.

> **Soal 6 [C6 – Create]** Untuk proyek PjBL kelompok, rancanglah spesifikasi perangkat keras awal: (a) diagram blok dan tabel alokasi pin bebas konflik, (b) justifikasi sensor, aktuator, dan konektivitas dengan WDM, (c) algoritma pemfilteran dan kendali bebas *chattering* dalam *pseudocode*, serta (d) BoM realistis dengan tautan datasheet!

**(a) Diagram blok dan alokasi pin SIARENG**

```
MPU6050 --SDA/SCL--> GPIO 21/22 ┐                 ┌ GPIO 26 --> LED hijau  (+R 220)
Tanah   --AOUT-----> GPIO 34    │    ESP32        │ GPIO 27 --> LED kuning (+R 220)
Hujan   --AO-------> GPIO 35    │    DevKit V1    │ GPIO 14 --> LED merah  (+R 220)
Tombol  --ke GND---> GPIO 15    ┘                 └ GPIO 25 --> Buzzer pasif (LEDC)
                                      │
                         Wi-Fi: HTTP POST / MQTT --> backend --> dashboard, Telegram
```
Listing 1: Diagram blok simpul SIARENG

| GPIO | Fungsi | Pemeriksaan Konflik |
|---|---|---|
| 21, 22 | I2C MPU6050 | Pin I2C bawaan, aman |
| 34, 35 | Sensor tanah dan hujan (analog) | ADC1, tetap terbaca saat Wi-Fi aktif; input saja sesuai kebutuhan |
| 26, 27, 14 | LED status | Keluaran digital; termasuk blok ADC2 tetapi tidak dipakai analog. GPIO 14 mengeluarkan PWM singkat saat *boot* sehingga LED merah dapat berkedip sesaat, tidak berbahaya |
| 25 | Buzzer PWM LEDC | Keluaran digital, aman |
| 15 | Tombol kalibrasi | Pin *strapping*, tetapi *pull-up* internal membuat level HIGH saat *boot*, sesuai nilai bawaan |
| 12 | Tidak dipakai | Pin *strapping* tegangan flash, sengaja dihindari |

**(b) Justifikasi dengan WDM**

| Kriteria Sensor Pergerakan Lereng | Bobot | MPU6050 | SW-420 (saklar getar) | SW-520D (saklar *tilt*) |
|---|---|---|---|---|
| Resolusi kemiringan | 0,35 | 5 | 1 | 1 |
| Ketahanan terhadap alarm palsu | 0,25 | 4 | 2 | 3 |
| Kemudahan integrasi | 0,15 | 4 | 5 | 5 |
| Harga | 0,25 | 4 | 5 | 5 |
| **Total** | **1,00** | **4,35** | **2,85** | **3,10** |

| Kriteria Konektivitas (lokasi uji) | Bobot | Wi-Fi | LoRa + Gateway | NB-IoT |
|---|---|---|---|---|
| Ketersediaan di lokasi uji | 0,30 | 5 | 3 | 3 |
| Biaya tahap prototipe | 0,25 | 5 | 2 | 2 |
| Ekosistem MQTT/TLS/OTA | 0,25 | 5 | 2 | 3 |
| Jangkauan & daya untuk lokasi terpencil | 0,20 | 2 | 5 | 4 |
| **Total** | **1,00** | **4,40** | **2,90** | **2,95** |

Keputusan: MPU6050 sebagai sensor kemiringan dan Wi-Fi untuk prototipe. LoRa menjadi pilihan berikutnya untuk lereng tanpa Wi-Fi; firmware sudah memisahkan modul pengiriman di `jaringan.h` sehingga mudah diganti.

**(c) Algoritma pemfilteran dan kendali**

```
setiap 200 ms:
    soil  <- 0,3 x persen(ADC34) + 0,7 x soil          // filter EMA
    rain  <- 0,3 x persen(ADC35) + 0,7 x rain
    g     <- EMA(akselerasi MPU6050)
    tilt  <- sudut(g, g_patokan)                        // tidak bergantung arah pasang

    kandidat <- BAHAYA   jika soil >= 80 DAN tilt >= 5 derajat
                WASPADA  jika soil >= 80 ATAU tilt >= 2 ATAU (soil >= 60 DAN rain >= 40)
                AMAN     selain itu

    jika kandidat > status dan bertahan >= 2 s  -> status naik     // histeresis waktu
    jika kandidat < status dan bertahan >= 6 s  -> status turun

    LED dan buzzer <- pola sesuai status (non-blocking, berbasis millis)
    kirim JSON tiap 2 s (aman), 1 s (waspada), 0,5 s (bahaya)
```
Listing 2: *Pseudocode* logika status SIARENG (`firmware/include/landslide_logic.h`)

**(d) Bill of Materials**

| Dokumen | Isi | Total |
|---|---|---|
| `RAB_SIARENG_hemat.xlsx` | Prototipe uji di breadboard, lengkap dengan tautan toko | ±Rp209.600 termasuk ongkir dan cadangan 10% |
| `RAB_SIARENG.xlsx` | Versi lengkap dengan box IP65, PCB, adaptor | ±Rp395.525 |

Lembar data acuan: ESP32 Series Datasheet (Espressif), MPU-6000/6050 Product Specification (InvenSense), serta dokumentasi modul sensor tanah kapasitif v1.2 dan modul hujan FC-37.
