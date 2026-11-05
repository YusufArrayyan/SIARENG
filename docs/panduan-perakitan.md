# Panduan Perakitan SIARENG Versi Lapangan

Panduan ini membawa SIARENG dari komponen lepas sampai menjadi alat yang terpasang di lereng dan bisa berjalan sendiri berhari-hari.
Dibanding RAB lengkap, versi ini menambah empat hal: **catu daya surya + baterai**, **soket dan terminal** agar komponen mudah diganti, **perlindungan air** untuk sensor, dan **tiang pemasangan**.

Kerjakan tahap demi tahap. Jangan lanjut ke tahap berikutnya sebelum uji di akhir tahap itu lolos.

| Tahap | Isi | Perkiraan waktu |
|---|---|---|
| 0 | Belanja dan siapkan alat | 1 minggu (menunggu kiriman) |
| 1 | Rakit dan uji di breadboard | 1 hari |
| 2 | Kalibrasi sensor | 2 jam |
| 3 | Pindahkan ke PCB lubang | 1 hari |
| 4 | Pasang catu daya surya | setengah hari |
| 5 | Siapkan box dan lindungi sensor | 1 hari |
| 6 | Rakit akhir dan uji 24 jam | 1–2 hari |
| 7 | Pasang di lereng | 1 hari |
| 8 | Perawatan | rutin |

> Alat ini adalah alarm lokal untuk pembelajaran, bukan sistem peringatan dini resmi. Semua ambang di firmware adalah nilai awal untuk demo, bukan ambang longsor sungguhan.

---

## Tahap 0 — Belanja dan alat kerja

### 0.1 Komponen dasar

Beli semua item di [`RAB_SIARENG.xlsx`](RAB_SIARENG.xlsx) bagian A, B, dan C.
Adaptor 5V di bagian C boleh dilewati karena tugasnya diganti panel surya. Adaptor tetap berguna untuk uji di meja.

### 0.2 Tambahan untuk versi lapangan

Harga di tabel ini **perkiraan, belum dicek di toko**. Cek ulang sebelum membeli.

| Komponen | Jumlah | Perkiraan harga | Fungsi |
|---|---|---|---|
| Pin header female 1x20 (atau 1x40 dipotong) | 2 | Rp5.000 | Soket ESP32 di PCB, jadi ESP32 bisa dicabut |
| Screw terminal block 2 pin dan 3 pin, jarak 5,08 mm | 6 | Rp10.000 | Sambungan kabel sensor luar dan daya, tanpa solder ulang |
| Modul TP4056 dengan proteksi baterai (6 kaki, ada IC DW01) | 1 | Rp8.000 | Mengisi baterai dari panel surya |
| Modul boost MT3608 | 1 | Rp10.000 | Menaikkan tegangan baterai menjadi 5 V untuk ESP32 |
| Baterai Li-ion 18650, merek jelas, ±3000 mAh | 2 | Rp80.000–120.000 | Cadangan daya malam dan saat mendung |
| Holder baterai 2x18650 | 1 | Rp8.000 | Tempat baterai, disambung paralel |
| Panel surya 6 V 5 W | 1 | Rp70.000–100.000 | Sumber daya utama |
| Dioda Schottky 1N5819 | 2 | Rp1.000 | Mencegah arus balik dari baterai ke panel saat malam |
| Saklar toggle ON/OFF kecil | 1 | Rp3.000 | Memutus daya tanpa membuka kabel |
| Spacer/standoff M3 + baut | 1 set | Rp10.000 | Membaut PCB dan MPU6050 ke dasar box |
| Silica gel sachet, heat shrink, cable ties | 1 set | Rp15.000 | Penyerap lembap dan perapian kabel |
| Lem epoksi 2 komponen (atau kuteks bening) | 1 | Rp15.000 | Melapisi bagian elektronik sensor tanah |
| Pipa besi 1/2" atau besi siku, panjang 1–1,2 m, + klem U | 1 | Rp40.000 | Tiang box di lereng |

Perkiraan tambahan: **Rp280.000–350.000**. Jika ditambah RAB lengkap (sekitar Rp395.000), total versi lapangan sekitar **Rp650.000–750.000**.

Dua baterai 3000 mAh dipasang paralel memberi sekitar 22 Wh. Firmware saat ini belum memakai WiFi, jadi ESP32 dan sensornya menarik sekitar 50–70 mA pada 5 V, atau 6–8 Wh per hari. Baterai cukup untuk sekitar 3 hari tanpa matahari. Panel 5 W di Bengkulu menghasilkan sekitar 12–15 Wh per hari saat cerah, lebih dari kebutuhan harian. Ukur sendiri arus alatmu di Tahap 4 untuk memastikan.

### 0.3 Alat kerja

Solder 40–60 W dan timah, multimeter, tang potong dan tang lancip, obeng, bor dengan mata bor 5 mm, 6 mm, dan 12,5 mm (untuk cable gland PG7), lem tembak, serta silikon bening.

---

## Tahap 1 — Rakit dan uji di breadboard

Tujuannya memastikan semua komponen hidup dan firmware berjalan di perangkat asli sebelum ada yang disolder.

### 1.1 Sambungan

**Semua sensor diberi daya 3,3 V, bukan 5 V.** ADC ESP32 hanya aman sampai 3,3 V. Sensor hujan yang diberi 5 V bisa mengeluarkan tegangan di atas batas itu.

| Komponen | Pin komponen | Ke ESP32 |
|---|---|---|
| MPU6050 | VCC / GND | 3V3 / GND |
| | SDA / SCL | GPIO 21 / GPIO 22 |
| Sensor tanah kapasitif | VCC / GND | 3V3 / GND |
| | AOUT | GPIO 34 |
| Modul sensor hujan (komparator) | VCC / GND | 3V3 / GND |
| | AO (bukan DO) | GPIO 35 |
| | 2 pin ke panel | ke panel hujan |
| Buzzer pasif | S (sinyal) / – | GPIO 25 / GND |
| | + (bila ada) | 3V3 |
| LED hijau | anoda (kaki panjang) | resistor 220 Ω, lalu GPIO 26 |
| LED kuning | anoda | resistor 220 Ω, lalu GPIO 27 |
| LED merah | anoda | resistor 220 Ω, lalu GPIO 14 |
| Ketiga LED | katoda (kaki pendek) | GND |
| Tombol kalibrasi | kaki 1 / kaki 2 | GPIO 15 / GND |

GPIO 34 dan 35 hanya bisa dipakai sebagai input. Karena itu keduanya dipakai untuk sensor analog.

### 1.2 Upload firmware

1. Buka `firmware/include/config.h`, ubah `#define SIMULASI 1` menjadi `0`. Biarkan `BUZZER_PASIF 1`.
2. Sambungkan ESP32 ke laptop dengan kabel data micro USB.
3. Di VS Code: PlatformIO → **Upload**, lalu **Monitor** (115200 baud).
4. Kalau upload gagal di tengah "Connecting...", tahan tombol **BOOT** di ESP32 sampai upload mulai berjalan.

### 1.3 Uji lolos jika

- [ ] Muncul `{"event":"boot",...}` lalu `{"event":"baseline_siap",...}` sekitar 2 detik kemudian.
- [ ] Tidak muncul `"MPU6050 tidak terdeteksi"`. Kalau muncul, periksa SDA/SCL dan pastikan VCC ke 3V3.
- [ ] Saat breadboard dimiringkan, nilai `tilt_delta_deg` naik.
- [ ] Saat sensor tanah dipegang atau dicelup air, nilai `soil_raw` berubah. Begitu juga `rain_raw` saat panel ditetesi air.
- [ ] Tombol mengirim `{"event":"kalibrasi_ulang",...}`.
- [ ] LED hijau menyala. Saat status naik, LED kuning atau merah menyala dan buzzer berbunyi.

Angka persen tanah dan hujan belum benar di tahap ini karena sensor belum dikalibrasi.

---

## Tahap 2 — Kalibrasi sensor

Firmware mengirim nilai ADC mentah di field `soil_raw` dan `rain_raw` (0–4095). Nilai ini dipakai untuk mengisi `config.h`.

### 2.1 Sensor tanah

1. **Kering:** biarkan sensor di udara selama 1 menit. Catat rata-rata `soil_raw`. Angka ini menjadi `SOIL_RAW_KERING`.
2. **Basah:** celupkan sensor ke segelas air sampai garis batas putih di badannya, jangan lebih dalam. Catat rata-ratanya. Angka ini menjadi `SOIL_RAW_BASAH`.
3. Lebih baik lagi, ulangi dengan tanah dari lokasi pemasangan: tanah kering angin untuk nilai kering, tanah yang disiram sampai becek untuk nilai basah.

### 2.2 Sensor hujan

1. **Kering:** lap panel sampai kering. Catat `rain_raw` sebagai `RAIN_RAW_KERING`.
2. **Basah:** siram panel sampai seluruh jalurnya basah. Catat sebagai `RAIN_RAW_BASAH`.

### 2.3 Isi dan uji

Isi keempat angka itu di blok `#else` pada `config.h`, lalu upload ulang. Pada kedua sensor, nilai mentah lebih tinggi saat kering. Kalau hasil ukurmu terbalik, tetap isi sesuai hasil ukur: rumus di firmware sudah menangani kedua arah.

Uji lolos jika `soil_pct` sekitar 0 di udara dan sekitar 100 di air, dan `rain_pct` sekitar 0 saat panel kering dan naik saat panel basah.
Setelah itu jalankan lima tahap skenario di [`simulasi-demo.md`](simulasi-demo.md) dengan sensor asli.

---

## Tahap 3 — Pindahkan ke PCB lubang

Breadboard mudah longgar kalau terkena getaran dan lembap. Untuk lapangan, rangkaian dipindah ke PCB lubang 7x9 cm.

### 3.1 Tata letak

```
+-------------------------------------------------+
| [T-daya 5V]   [=== soket female ESP32 kiri ===] |
|               [          ESP32 (dicabut)     ] |
| [T-tanah 3P]  [=== soket female ESP32 kanan ==] |
| [T-hujan 3P]                                    |
| [T-MPU 4P]    R R R      [T-LED/tombol ke tutup]|
| [T-buzzer]                                      |
+-------------------------------------------------+
T = screw terminal block
```

- **ESP32 tidak disolder langsung.** Solder dua baris pin header female, lalu tancapkan ESP32 ke situ. Jika ESP32 rusak, cukup cabut dan ganti.
- **Semua kabel yang keluar dari PCB lewat terminal block:** daya, sensor tanah, modul hujan, MPU6050, buzzer, dan kabel ke LED/tombol di tutup.
- **Resistor LED tetap di PCB.** LED dan tombol di tutup cukup disambung dengan kabel.
- **MPU6050 tidak dipasang di PCB.** Sensor ini dibaut sendiri ke dasar box (Tahap 5) dan disambung dengan 4 kabel ke terminal.
- Buat satu jalur 3V3 dan satu jalur GND yang panjang di pinggir PCB sebagai "rel", lalu ambil daya untuk semua terminal dari situ.

### 3.2 Uji sebelum memberi daya

Dengan multimeter mode kontinuitas (bunyi beep):

- [ ] 3V3 ke GND **tidak** berbunyi. Kalau berbunyi, ada korsleting. Cari dan perbaiki dulu.
- [ ] 5V/VIN ke GND **tidak** berbunyi.
- [ ] Setiap pin GPIO tersambung ke terminal yang benar, sesuai tabel di Tahap 1.

Setelah lolos, tancapkan ESP32, sambungkan semua sensor ke terminal, lalu ulangi uji Tahap 1.3 dan 2.3.

---

## Tahap 4 — Catu daya surya

### 4.1 Rangkaian

```
Panel surya 6V (+) --> 1N5819 --> TP4056 IN+         TP4056 B+ / B-  <--> 2x18650 paralel
Panel surya 6V (-) -------------> TP4056 IN-
TP4056 OUT+ --> saklar --> MT3608 VIN+    MT3608 VOUT+ --> terminal 5V --> ESP32 VIN
TP4056 OUT- ------------> MT3608 VIN-     MT3608 VOUT- --> terminal GND --> ESP32 GND
```

### 4.2 Langkah dan peringatan

1. **Atur MT3608 dulu, sebelum disambung ke ESP32.** Beri daya dari baterai, ukur VOUT dengan multimeter, lalu putar trimpot kecil di modul sampai terbaca **5,0–5,1 V**. Modul baru sering keluar dengan tegangan jauh lebih tinggi, dan tegangan itu bisa merusak ESP32.
2. **Baterai paralel harus setegangan.** Sebelum dimasukkan ke holder, isi penuh keduanya atau ukur keduanya dan pastikan selisihnya di bawah 0,1 V.
3. **Perhatikan polaritas baterai.** Terbalik sedikit saja bisa membakar TP4056.
4. **Matikan saklar daya saat upload firmware lewat USB laptop**, supaya dua sumber 5 V tidak bertemu.

### 4.3 Uji lolos jika

- [ ] Dengan saklar ON dan USB laptop dicabut, alat menyala: LED hijau menyala setelah 2 detik, dan saat box dimiringkan lebih dari 5 derajat sambil sensor tanah dicelup air, LED merah dan buzzer aktif.
- [ ] Panel di bawah matahari menyalakan LED pengisian di TP4056 (merah = mengisi, biru/hijau = penuh).
- [ ] Arus yang diukur seri di jalur OUT+ TP4056 sekitar 50–100 mA. Catat angkanya untuk laporan.

---

## Tahap 5 — Box dan perlindungan sensor

### 5.1 Melubangi box IP65

| Lubang | Posisi | Ukuran bor |
|---|---|---|
| 3 LED | Tutup, mudah terlihat dari bawah lereng | 5 mm |
| Tombol kalibrasi | Tutup | sesuai diameter tombol |
| 3 cable gland PG7 (sensor tanah, panel hujan, panel surya) | **Sisi bawah box**, supaya air tidak menetes masuk | 12,5 mm |
| 2–3 lubang suara buzzer | Sisi bawah, dekat buzzer | 2 mm |

Setelah LED dan tombol dipasang, tutup celahnya dengan silikon bening dari sisi luar dan dalam.

### 5.2 Isi box

- Baut **PCB** ke dasar box dengan spacer M3.
- Baut **MPU6050** langsung ke dasar box dengan spacer pendek, **sekaku mungkin**. Kalau MPU6050 bisa goyang, pembacaan kemiringan ikut bergeser. Catat arah sumbu X/Y di box sebagai bahan laporan.
- Rekatkan **holder baterai, TP4056, dan MT3608** di dinding box dengan lem tembak atau double tape tebal.
- Masukkan 2 sachet **silica gel**. Ganti setiap kali box dibuka.

### 5.3 Melindungi sensor di luar box

- **Sensor tanah kapasitif:** bagian atas sensor (komponen elektronik dan konektor) dilapisi epoksi atau 2–3 lapis kuteks bening, lalu dibungkus heat shrink. Tepi PCB yang terpotong juga dilapisi. Hanya bagian di bawah garis putih yang boleh masuk tanah.
- **Panel hujan:** pasang di braket atau di atas tutup dengan kemiringan **30–45°**, supaya air hujan mengalir turun dan tidak menggenang. Modul komparatornya tetap di dalam box.
- **Panel surya:** pasang di atas tiang, menghadap langit terbuka, dengan kemiringan sekitar 10–15°. Pada posisi ini panel tetap terkena sinar matahari sepanjang tahun di Bengkulu, dan air hujan bisa membersihkan permukaannya.

---

## Tahap 6 — Rakit akhir dan uji 24 jam

1. Sambungkan semua kabel ke terminal, kencangkan cable gland, tutup box.
2. Letakkan alat di halaman terbuka dengan panel surya terkena matahari.
3. Nyalakan saklar, tanpa USB laptop. Catat waktu mulai, lalu biarkan selama **24 jam**. Periksa LED hijau di sore hari, malam hari, dan keesokan paginya.

Uji lolos jika:

- [ ] Alat tetap menyala semalaman hanya dari baterai.
- [ ] Tidak ada reset sendiri. Tanda reset: LED kuning menyala lagi sebentar (fase kalibrasi saat boot) padahal tidak ada yang menekan tombol.
- [ ] Setelah disiram air (simulasi hujan), tidak ada air masuk ke box.
- [ ] Skenario bahaya (tanah dibasahi dan box dimiringkan) tetap memicu LED merah dan buzzer.

---

## Tahap 7 — Pemasangan di lereng

### 7.1 Sebelum berangkat

- Minta izin pemilik lahan dan beri tahu warga sekitar atau perangkat desa. Kalau lereng termasuk daerah rawan yang dipantau BPBD, kabari BPBD juga.
- Jangan memasang saat hujan atau tepat setelah hujan lebat. Pergi minimal berdua.
- Catat koordinat GPS dan foto lokasi untuk laporan.

### 7.2 Memasang

1. **Tiang:** tanam pipa atau besi siku sedalam **50–70 cm** di badan lereng yang ingin dipantau, bukan di tanah keras di luar lereng. Jika lereng bergerak, tiang ikut bergerak dan MPU6050 merasakannya.
2. **Box:** ikat ke tiang dengan klem U, posisi tegak, sekitar 50 cm di atas tanah.
3. **Sensor tanah:** tanam tegak 1 m dari tiang, sampai garis batas sensor (sekitar 10–15 cm dari permukaan). Padatkan tanah di sekitarnya dengan tangan supaya tidak ada rongga udara.
4. **Kabel:** rapikan dengan cable ties ke tiang. Buat sedikit lengkungan ke bawah sebelum kabel masuk gland, supaya air menetes di lengkungan dan tidak mengalir ke gland.
5. **Kalibrasi kemiringan:** setelah semua terpasang dan tiang tidak bergoyang, **tekan tombol kalibrasi**. Posisi saat itu menjadi baseline "normal". LED hijau menyala.

### 7.3 Uji di lokasi

Siram sekitar sensor tanah dengan beberapa liter air. Nilai tanah harus naik. Kalau tanah mencapai di atas 60% dan panel hujan ikut disiram, status naik ke waspada (LED kuning). Setelah itu biarkan alat kembali ke aman.

---

## Tahap 8 — Perawatan

| Kapan | Yang dicek |
|---|---|
| Setiap minggu | LED masih menyala, panel surya bersih dari daun dan lumpur, tiang masih tegak |
| Setiap 2–4 minggu | Silica gel (ganti bila berubah warna), tegangan baterai (di atas 3,6 V saat siang), jalur panel hujan tidak berkarat |
| Setiap 3–6 bulan | Ganti panel hujan bila jalurnya sudah menghitam atau terkelupas, cek lapisan pelindung sensor tanah |
| Setelah tiang terganggu (tersenggol, diperbaiki) | Tekan tombol kalibrasi lagi agar baseline baru tercatat |

---

## Masalah yang sering muncul

| Gejala | Kemungkinan penyebab | Solusi |
|---|---|---|
| `MPU6050 tidak terdeteksi` | SDA/SCL tertukar atau kabel longgar | Cek GPIO 21 = SDA, GPIO 22 = SCL, VCC ke 3V3 |
| `soil_raw` atau `rain_raw` selalu 0 atau 4095 | Kabel AO lepas, atau sensor diberi 5 V | Cek sambungan dan pastikan VCC ke 3V3 |
| Alat reset sendiri saat buzzer berbunyi | Tegangan turun, baterai lemah | Isi baterai, cek MT3608 tetap di 5,0–5,1 V |
| Status langsung waspada setelah dipasang | Baseline diambil saat tiang belum stabil | Tunggu tiang diam, lalu tekan tombol kalibrasi |
| Upload gagal "Failed to connect" | ESP32 belum masuk mode upload | Tahan tombol BOOT saat "Connecting..." |
| Port COM tidak muncul di Windows | Driver CP2102/CH340 belum terpasang | Pasang driver sesuai chip USB di board |
| Baterai habis dalam 1–2 hari | Panel tertutup bayangan atau terlalu kecil | Pindahkan panel ke tempat terbuka, atau ganti panel 10 W |

---

## Langkah berikutnya

Saat ini SIARENG hanya memberi alarm di lokasi (LED dan buzzer) dan mengirim data lewat kabel USB. Pengiriman data jarak jauh (WiFi/MQTT ke backend, atau LoRa untuk lereng tanpa sinyal) menjadi tahap berikutnya, sesuai folder `edge-gateway/` dan `backend-api/`.
Kalau WiFi diaktifkan, konsumsi daya naik sekitar dua kali lipat. Ukur ulang konsumsinya, lalu pertimbangkan panel 10 W atau mode deep sleep di antara pembacaan sensor.
