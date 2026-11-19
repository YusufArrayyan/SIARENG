# Tugas Minggu 2: Matriks Keputusan Berbobot dan Problem Set Modul C1–C6

Proyek: SIARENG (Siaga Lereng)
Laporan praktikum Lab-1 ada di [`laporan-lab01-minggu-02.md`](laporan-lab01-minggu-02.md). Dokumen ini berisi:

1. **Lembar Kerja Terstruktur Minggu 2**: matriks keputusan berbobot (WDM) dan draf BoM untuk Kasus B (kebun kopi Rejang Lebong).
2. **Problem Set modul C1–C6**. Soal C6 dikerjakan langsung untuk proyek SIARENG, sekaligus menjadi bahan Proposal Milestone 1.

> Harga di bagian BoM Kasus B adalah **perkiraan** dari kisaran pasar daring, belum dicek per toko. Harga SIARENG di C6 sudah dicek di Tokopedia (lihat file RAB).

---

## Bagian A. WDM dan draf BoM Kasus B: Smart Farming Kebun Kopi Rejang Lebong

**Kendala utama kasus:** 6 blok kebun berjarak 150–850 m dari pondok, tanpa listrik PLN, 2 blok di lembah tanpa sinyal seluler. Greenhouse berjarak 25 m dari pondok. Listrik dan internet hanya ada di pondok. Anggaran ≤ Rp4.500.000, biaya bulanan minimal, dan baterai paling sering dirawat 6 bulan sekali.

**Tiga kandidat arsitektur:**

- **Opsi 1, Full Wi-Fi Extender:** setiap blok memakai ESP32 Wi-Fi, ditambah beberapa *repeater*/antena Wi-Fi jarak jauh dari pondok.
- **Opsi 2, ESP32 + SIM seluler:** setiap blok punya modem 4G/NB-IoT sendiri dan mengirim langsung ke *cloud*.
- **Opsi 3, Hibrida:** ESP32 + LoRa (SX1276, 920–923 MHz) di 6 blok kebun, ESP32 Wi-Fi di greenhouse, dan Raspberry Pi *gateway* di pondok.

**Skor 1–5 (5 = terbaik):**

| Kriteria | Bobot | Opsi 1 | Opsi 2 | Opsi 3 | Alasan teknis |
|---|---|---|---|---|---|
| 1. Jangkauan dan penetrasi kanopi | 0,25 | 1 | 2 | 5 | Wi-Fi 2,4 GHz efektif 30–80 m dan teredam berat oleh dedaunan, sehingga blok 850 m perlu banyak *repeater* berdaya. Seluler gagal di 2 blok lembah tanpa sinyal. LoRa sub-GHz menjangkau 2–15 km dan lebih tahan halangan. |
| 2. Efisiensi daya / umur baterai | 0,25 | 2 | 2 | 5 | Wi-Fi TX 80–240 mA dan proses menyambung ulang lama setiap bangun. Modem seluler juga boros saat registrasi jaringan. LoRa TX ~120 mA hanya beberapa ratus milidetik, ditambah *deep sleep* 10–150 µA, sehingga baterai bisa bertahan berbulan-bulan. |
| 3. Kecukupan I/O, ADC, komputasi | 0,15 | 5 | 4 | 4 | Ketiganya memakai ESP32 (ADC1 12-bit, I2C). Opsi 2 dan 3 memakai beberapa pin untuk UART/SPI modem atau radio, tetapi pin sisanya masih cukup. |
| 4. Kematangan ekosistem dan keamanan | 0,15 | 5 | 4 | 3 | Wi-Fi mendukung TCP/IP penuh, MQTT/TLS, dan OTA. Seluler juga IP. LoRa non-IP: perlu *gateway* penerjemah ke MQTT, *payload* biner ringkas, dan enkripsi AES di tingkat aplikasi. |
| 5. Efisiensi biaya BoM dan OPEX | 0,20 | 2 | 1 | 4 | Opsi 1: perlu *repeater* outdoor dan panel surya untuk tiap *repeater*. Opsi 2: modem + 6 kartu SIM bulanan, bertentangan dengan permintaan biaya bulanan minimal. Opsi 3: tanpa biaya bulanan, *gateway* RPi dipakai bersama. |
| **Total S<sub>j</sub> = Σ w<sub>i</sub> r<sub>ij</sub>** | **1,00** | **2,65** | **2,40** | **4,35** | **Keputusan: Opsi 3** |

Rincian hitungan:

- **Opsi 1:** 0,25(1) + 0,25(2) + 0,15(5) + 0,15(5) + 0,20(2) = 0,25 + 0,50 + 0,75 + 0,75 + 0,40 = **2,65**
- **Opsi 2:** 0,25(2) + 0,25(2) + 0,15(4) + 0,15(4) + 0,20(1) = 0,50 + 0,50 + 0,60 + 0,60 + 0,20 = **2,40**
- **Opsi 3:** 0,25(5) + 0,25(5) + 0,15(4) + 0,15(3) + 0,20(4) = 1,25 + 1,25 + 0,60 + 0,45 + 0,80 = **4,35**

**Uji sensitivitas:** jika bobot jangkauan turun 10 poin (0,25 → 0,15) dan bobot ekosistem naik 10 poin (0,15 → 0,25), skor menjadi Opsi 1 = 3,05, Opsi 2 = 2,60, Opsi 3 = 4,15. Pemenangnya tetap Opsi 3, jadi keputusan ini tidak rapuh terhadap perubahan bobot.

**Pilihan sensor lengas tanah:** *Capacitive Soil Moisture Sensor v1.2*, karena elektrodanya tertutup lapisan dan tidak terkorosi. Sensor garpu resistif rusak dalam hitungan minggu akibat elektrolisis DC. Bagian elektronik di atas garis batas perlu dilapisi epoksi.

**Catu daya simpul kebun:** panel surya 6 V 5 W + 2 × 18650 paralel (~6000 mAh) + TP4056 + regulator 3,3 V *low-dropout* (bukan modul *boost* 5 V, supaya tidak ada rugi konversi dua kali). ESP32 bangun 15 menit sekali.

**Draf BoM Opsi 3 (perkiraan):**

| Bagian | Isi per unit | Harga per unit | Jumlah | Subtotal |
|---|---|---|---|---|
| Simpul kebun | ESP32 (Rp82.000), LoRa SX1276 Ra-02 (Rp75.000), sensor tanah kapasitif (Rp12.000), DHT22 (Rp24.000), BH1750 cahaya (Rp20.000), panel surya 5 W (Rp85.000), 2 × 18650 (Rp100.000), TP4056 + LDO (Rp18.000), box IP65 (Rp45.000) | Rp461.000 | 6 | Rp2.766.000 |
| Simpul greenhouse | ESP32, sensor tanah, DHT22, BH1750, relai 2 kanal, katup solenoida 12 V, kipas kabut 12 V, adaptor 12 V | Rp405.000 | 1 | Rp405.000 |
| Gateway pondok | Raspberry Pi 4 2 GB set minimal (Rp1.100.000) + LoRa SX1276 (Rp75.000) | Rp1.175.000 | 1 | Rp1.175.000 |
| **Total** | | | | **Rp4.346.000** (di bawah plafon Rp4,5 juta, sisa ±Rp154.000) |

Catatan: dengan satu modul SX1276 di gateway, komunikasinya **LoRa titik-ke-titik**, bukan LoRaWAN penuh. *Gateway* LoRaWAN 8 kanal (konsentrator SX1302) harganya di atas Rp1,5 juta sehingga melewati plafon. Untuk 6 simpul yang mengirim 15 menit sekali, LoRa titik-ke-titik dengan jadwal kirim yang diacak sudah cukup.

---

## Bagian B. Problem Set Modul Minggu 2

### Soal 1 [C1]

**(a) Sensor analog vs digital:**

| | Analog | Digital |
|---|---|---|
| Keluaran | Tegangan kontinu, dibaca lewat ADC mikrokontroler, perlu kalibrasi di *firmware* | Paket bit lewat bus (I2C, satu kabel, UART). ADC dan kalibrasi sudah ada di dalam sensor |
| Contoh | Sensor tanah kapasitif v1.2, LDR, sensor gas MQ-2 | DHT22, BME280 (I2C), HC-SR04 (lebar pulsa), PZEM-004T (UART Modbus) |

**(b) Pin ADC1 ESP32 (aman saat Wi-Fi aktif):** GPIO 32, 33, 34, 35, 36 (VP), dan 39 (VN). GPIO 34–39 hanya bisa menjadi input.

**(c) Lima teknologi konektivitas dari jangkauan terpendek ke terjauh:** Zigbee/Thread (10–30 m per lompatan), BLE 5.x (10–50 m), Wi-Fi (30–80 m), NB-IoT/LTE-M (1–10 km, mengikuti BTS), LoRa/LoRaWAN (2–15 km).

### Soal 2 [C2]

**(a) Raspberry Pi tidak cocok sebagai simpul sensor tanah bertenaga surya kecil.** RPi menarik 2,7–3,5 W saat diam dan tidak punya mode *deep sleep* orde mikroampere. Dalam sehari ia butuh 65–85 Wh, padahal panel 5 W hanya menghasilkan sekitar 15–20 Wh per hari. Selain itu RPi tidak punya ADC sehingga butuh chip tambahan untuk sensor analog, dan kartu microSD-nya bisa rusak saat baterai habis mendadak. ESP32 dengan *deep sleep* cukup memakai beberapa mAh per hari. Kecepatan prosesor RPi tidak dibutuhkan untuk membaca satu sensor 15 menit sekali.

**(b) LoRaWAN melarang JSON panjang.** *Payload* maksimum hanya 51–222 byte tergantung *spreading factor*, laju data 0,3–27 kbps, dan regulasi pita ISM membatasi *duty cycle* atau waktu siar (*airtime*). JSON boros karena nama kunci dan tanda kutip ikut dikirim setiap kali. Contohnya `{"soil_pct":45.2,"temp_c":27.1}` = 32 byte, sedangkan versi biner cukup 4 byte (2 × `int16` dikali 10). Semakin panjang paket, semakin lama radio menyala (boros baterai), semakin besar peluang tabrakan dengan simpul lain, dan semakin cepat kuota waktu siar habis. Karena itu dipakai CBOR atau *byte packing*.

### Soal 3 [C3]

Diketahui: sensor 0,5 V (0 bar) sampai 4,5 V (10 bar), linear. Pembagi tegangan R1 = 10 kΩ (seri), R2 = 20 kΩ (ke GND), sehingga V<sub>out</sub> = V<sub>in</sub> × 20/30 = 0,667 × V<sub>in</sub>.

**(a) Rentang tegangan ke pin ESP32:** 0,5 × 0,667 = **0,333 V** sampai 4,5 × 0,667 = **3,00 V**. Aman, di bawah 3,3 V.

**(b) Cacah ADC pada 6,0 bar:**

```
V_in  = 0,5 + (4,0 / 10) × 6,0 = 2,90 V
V_out = 2,90 × 2/3 = 1,933 V
D     = 1,933 / 3,3 × 4095 ≈ 2399
```

(Ini nilai ideal. ADC ESP32 asli menyimpang beberapa persen, jadi gunakan `analogReadMilliVolts()`.)

**(c) Umur baterai LiFePO4 4000 mAh (η = 0,80):** t<sub>aktif</sub> = 2,5 s pada 140 mA, t<sub>tidur</sub> = 600 − 2,5 = 597,5 s pada 80 µA.

```
I_avg = (140 × 2,5 + 0,08 × 597,5) / 600 = (350 + 47,8) / 600 = 0,663 mA
T     = 4000 × 0,80 / 0,663 ≈ 4826 jam ≈ 201 hari (≈ 6,6 bulan)
```

### Soal 4 [C4]. Tiga kesalahan prototipe penyiram tanaman

| Kesalahan | Penyebab | Perbaikan |
|---|---|---|
| 1. Pembacaan tanah kacau setelah `WiFi.begin()` | GPIO 25 termasuk **ADC2**. Radio Wi-Fi memakai ADC2, sehingga `analogRead()` di pin ADC2 gagal atau berisi sampah saat Wi-Fi aktif. | Pindahkan sensor ke pin **ADC1**, misalnya GPIO 34, dan pakai `analogReadMilliVolts()`. |
| 2. ESP32 sesekali gagal *boot* saat relai terpasang | GPIO 12 adalah **pin *strapping*** (MTDI) yang menentukan tegangan flash internal saat *boot*. Modul relai yang menarik pin ini ke HIGH saat menyala membuat flash disetel ke 1,8 V, sehingga ESP32 tidak bisa *boot*. | Pindahkan relai ke pin aman seperti GPIO 26. Hindari GPIO 0, 2, 5, 12, dan 15 untuk beban yang bisa menarik level saat *boot*. |
| 3. Relai bergetar belasan kali per menit | **Ambang tunggal 45%**: derau ±0,5% di sekitar 45% membuat kondisi `if` berganti-ganti (*chattering*). | Histeresis dua ambang (pompa ON < 35%, OFF ≥ 60%, di antaranya status dipertahankan), ditambah *moving average* pada pembacaan. Lihat Lab-1. |

### Soal 5 [C5]. WDM pemantauan suhu 25 truk ikan lintas kabupaten

| Kriteria | Bobot | A: Wi-Fi hotspot HP sopir | B: LoRaWAN, 3 gateway | C: LTE-M/NB-IoT + buffer flash |
|---|---|---|---|---|
| Cakupan sepanjang rute Pulau Baai–Curup–Mukomuko | 0,30 | 2 (tergantung HP sopir menyala dan berkuota) | 1 (3 gateway di kantor dinas tidak mencakup ratusan km jalan pegunungan) | 4 (mengikuti BTS, lubang sinyal ditutup buffer) |
| Keandalan dan keutuhan data | 0,25 | 1 (HP mati, kuota habis, atau sopir lupa = data hilang) | 2 (di luar jangkauan gateway = data hilang) | 5 (buffer flash + QoS 1 + `seq`) |
| Latensi peringatan suhu | 0,15 | 3 | 2 | 4 |
| Biaya infrastruktur (CAPEX) | 0,15 | 5 (hampir nol) | 2 (gateway, menara, instalasi) | 3 (modem Rp150–300 ribu per truk) |
| Biaya bulanan (OPEX) dan pengelolaan | 0,15 | 3 (kuota sopir, tidak terkontrol) | 4 (tanpa SIM, tetapi gateway perlu dirawat) | 3 (SIM M2M × 25, kuota kecil) |
| **Total** | **1,00** | **2,50** | **2,00** | **3,95** |

**Rekomendasi: Kandidat C.** Truk bergerak melintasi wilayah luas yang hanya terjangkau jaringan operator seluler, dan LTE-M/NB-IoT memang dirancang untuk aset bergerak dengan mode hemat daya (PSM/eDRX). Kelemahannya, yaitu lubang sinyal di jalur pegunungan, ditutup oleh buffer flash lokal: data tetap tercatat dengan stempel waktu dan dikirim setelah sinyal kembali. Kandidat A gugur karena bergantung pada perilaku sopir. Kandidat B gugur karena tiga gateway tetap tidak mencakup rute ratusan kilometer. Uji sensitivitas: menaikkan bobot CAPEX ke 0,30 (mengurangi cakupan ke 0,15) menghasilkan A = 2,95, B = 2,15, C = 3,80, jadi C tetap unggul.

### Soal 6 [C6]. Spesifikasi perangkat keras SIARENG (bahan Milestone 1)

**(a) Diagram blok dan alokasi pin bebas konflik**

```
         +----------------- ESP32 DevKit V1 -----------------+
MPU6050 --| GPIO 21 SDA / GPIO 22 SCL (I2C, 0x68)              |-- GPIO 26  LED hijau  (+R 220)
Tanah   --| GPIO 34 (ADC1, input-only)                         |-- GPIO 27  LED kuning (+R 220)
Hujan   --| GPIO 35 (ADC1, input-only)                         |-- GPIO 14  LED merah  (+R 220)
Tombol  --| GPIO 15 (INPUT_PULLUP, ke GND)                     |-- GPIO 25  Buzzer pasif (LEDC)
          |            Wi-Fi -> HTTP POST / MQTT -> backend    |
          +----------------------------------------------------+
```

| GPIO | Fungsi | Pemeriksaan konflik |
|---|---|---|
| 21, 22 | I2C MPU6050 | Pin I2C bawaan, aman |
| 34, 35 | Sensor tanah dan hujan (analog) | **ADC1**, tetap terbaca saat Wi-Fi aktif. Input saja, sesuai kebutuhan |
| 26, 27, 14 | LED status | Keluaran digital. Termasuk blok ADC2, tetapi tidak dipakai untuk analog, jadi aman. GPIO 14 mengeluarkan sinyal PWM singkat saat *boot*: LED merah bisa berkedip sesaat, tidak berbahaya |
| 25 | Buzzer (PWM LEDC) | Keluaran digital, aman |
| 15 | Tombol kalibrasi | Pin *strapping*, tetapi pakai *pull-up* internal dan tombol ke GND (aktif LOW). Saat tidak ditekan level HIGH, sesuai nilai bawaannya, sehingga *boot* normal |
| 12 | **Tidak dipakai** | Pin *strapping* tegangan flash, sengaja dihindari |

**(b) Justifikasi dengan WDM**

*Sensor pergerakan lereng:*

| Kriteria | Bobot | MPU6050 (akselerometer 3 sumbu) | SW-420 (saklar getar) | Sensor *tilt* bola (SW-520D) |
|---|---|---|---|---|
| Resolusi kemiringan | 0,35 | 5 (± 0,1° setelah filter, sudut kontinu) | 1 (hanya ada/tidak getaran) | 1 (hanya miring/tidak, ambang tetap ~15–45°) |
| Tahan alarm palsu | 0,25 | 4 (sudut dibanding patokan + filter) | 2 (tersenggol sedikit langsung memicu) | 3 |
| Kemudahan integrasi | 0,15 | 4 (I2C, perlu kode baca register) | 5 | 5 |
| Harga | 0,25 | 4 (Rp32.000) | 5 (Rp10.000) | 5 (Rp3.000) |
| **Total** | **1,00** | **4,35** | **2,85** | **3,10** |

*Konektivitas (lokasi uji dekat kampus/permukiman, ada Wi-Fi atau hotspot):*

| Kriteria | Bobot | Wi-Fi | LoRa + gateway | NB-IoT |
|---|---|---|---|---|
| Ketersediaan di lokasi uji | 0,30 | 5 | 3 (perlu gateway sendiri) | 3 (perlu SIM, cakupan NB-IoT terbatas) |
| Biaya tahap prototipe | 0,25 | 5 (Rp0 tambahan) | 2 (2 modul + RPi) | 2 (modem + SIM) |
| Ekosistem (MQTT/TLS/OTA) | 0,25 | 5 | 2 | 3 |
| Jangkauan dan daya untuk lokasi terpencil | 0,20 | 2 | 5 | 4 |
| **Total** | **1,00** | **4,40** | **2,90** | **2,95** |

Keputusan: **Wi-Fi untuk prototipe**. Untuk pemasangan di lereng tanpa Wi-Fi, LoRa menjadi pilihan berikutnya, dan firmware sudah memisahkan pengiriman di `jaringan.h` supaya mudah diganti.

**(c) Algoritma pemfilteran dan kendali bebas *chattering***

```text
setiap 200 ms:
    soil  ← EMA(0,3 × persen(ADC34) + 0,7 × soil)          // filter EMA
    rain  ← EMA(0,3 × persen(ADC35) + 0,7 × rain)
    g     ← EMA(akselerasi MPU6050)
    tilt  ← sudut(g, g_patokan)                              // tidak bergantung arah pasang

    kandidat ← BAHAYA   jika soil ≥ 80 DAN tilt ≥ 5°
               WASPADA  jika soil ≥ 80 ATAU tilt ≥ 2° ATAU (soil ≥ 60 DAN rain ≥ 40)
               AMAN     selain itu

    // histeresis waktu (anti-chattering status):
    jika kandidat > status dan bertahan ≥ 2 s  → status naik
    jika kandidat < status dan bertahan ≥ 6 s  → status turun

    LED/buzzer ← pola sesuai status (non-blocking, berbasis millis)
    kirim JSON tiap 2 s (aman), 1 s (waspada), 0,5 s (bahaya)
```

Implementasi lengkapnya ada di `firmware/include/landslide_logic.h` dan sudah diuji di PC (`firmware/test_host/test_logic.cpp`).

**(d) Bill of Materials**

Rincian beserta link toko ada di dua file:

| File | Isi | Total |
|---|---|---|
| [`RAB_SIARENG_hemat.xlsx`](RAB_SIARENG_hemat.xlsx) | Prototipe uji di breadboard | ±Rp209.600 (termasuk ongkir dan cadangan 10%) |
| [`RAB_SIARENG.xlsx`](RAB_SIARENG.xlsx) | Versi lengkap dengan box IP65, PCB, adaptor | ±Rp395.525 |

Lembar data acuan: ESP32 Series Datasheet (Espressif), MPU-6000/6050 Product Specification (InvenSense), dan dokumentasi modul sensor tanah kapasitif v1.2 serta modul hujan FC-37/YL-83.
