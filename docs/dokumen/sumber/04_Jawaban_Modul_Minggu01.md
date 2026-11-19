---
berkas: Jawaban_Modul_Minggu01_SIARENG
jenis: LEMBAR JAWABAN
unit: PRODI S1 | INFORMATIKA | Jurusan Teknik Informatika | Fakultas Teknik UNIB
judul: LEMBAR JAWABAN MINGGU KE-1
subjudul: LK-1 Kasus A & Problem Set Fondasi Arsitektur IoT
kolom: Minggu=1 dari 16 | Kelompok=SIARENG | Sub-CPMK=Sub-CPMK 1.1
kepala_kiri: Lembar Jawaban Minggu 1 — Teknologi IoT
kepala_kanan: Modul 1: Fondasi & Arsitektur Referensi IoT
kaki: Kelompok SIARENG · Kurikulum OBE — Standar SN-Dikti & LAM Infokom
---

> **Capaian Pembelajaran Minggu Ke-1 (Sub-CPMK 1.1 — Level C2, A2)**
> Mahasiswa mampu menjelaskan konsep, karakteristik, dan arsitektur referensi berlapis IoT, serta memetakan komponen sistem IoT pada kasus lokal ke dalam arsitektur tersebut.
> Dokumen ini memuat dua luaran: **Lembar Kerja Mahasiswa 1 (LK-1)** analisis Kasus A (bobot 1% NA) dan **jawaban Problem Set Minggu 1** level C1–C6.

| No | Peran Rekayasa | Nama Anggota | NPM |
|---|---|---|---|
| 1 | Device & Firmware Engineer | ........................................ | .................... |
| 2 | Back-End & Data Engineer | ........................................ | .................... |
| 3 | Security & DevOps Engineer | ........................................ | .................... |
| 4 | Dashboard Engineer & Project Manager | ........................................ | .................... |

## Bagian 1 — Lembar Kerja Mahasiswa 1 (LK-1): Analisis Arsitektur Kasus A

> **Studi Kasus A: Sistem Peringatan Dini Banjir Terpadu DAS Air Bengkulu.** Lima pos pantau dari hulu (Bengkulu Tengah) hingga muara (Rawa Makmur, Tanjung Agung) memantau tinggi muka air, curah hujan, dan kecepatan arus setiap 1 menit. Dua pos hulu tanpa Wi-Fi, sinyal seluler fluktuatif, dan hanya bertenaga surya. Jika air naik ≥ 15 cm dalam 10 menit, sistem wajib mempercepat pengiriman menjadi 10 detik, membunyikan sirene hilir, dan memberi peringatan ke BPBD serta warga dengan latensi < 3 detik.

| Lapisan Arsitektur | Pertanyaan Panduan Analisis Kasus A | Hasil Pemetaan & Justifikasi Tim Mahasiswa |
|---|---|---|
| 1. Lapisan Persepsi | Sensor dan aktuator apa saja yang dibutuhkan di pos hulu dan pos hilir? Mengapa perlu manajemen daya (*deep sleep*) di pos hulu? | **Hulu:** sensor ultrasonik tahan air JSN-SR04T atau radar level untuk tinggi muka air, penakar hujan *tipping bucket* (pulsa dibaca lewat interupsi), sensor arus permukaan, ESP32, panel surya + baterai LiFePO4. **Hilir:** sensor serupa ditambah sirene 12 V lewat relai/MOSFET dan lampu strobo. **Deep sleep di hulu:** ESP32 yang terus aktif dengan radio menarik sekitar 120 mA dan menghabiskan baterai 3000 mAh dalam sekitar 20 jam, padahal musim hujan berarti mendung berhari-hari. Dengan siklus ukur tiap 1 menit lalu tidur, arus rata-rata turun ke orde 1–3 mA; pulsa penakar hujan tetap terhitung lewat EXT0 atau koprosesor ULP. |
| 2. Lapisan Transpor & Edge | Teknologi konektivitas apa yang paling sesuai untuk pos hulu vs pos kota? Apa peran *edge gateway* jika koneksi internet terputus sementara? | **Hulu:** LoRa/LoRaWAN AS923-2 menuju *gateway* di titik berlistrik dan berinternet (kantor desa atau pos tengah), jangkauan 2–15 km dengan daya sangat rendah; modem NB-IoT/4G hanya cadangan. **Kota/hilir:** Wi-Fi atau 4G karena tersedia listrik PLN. **Edge gateway (Raspberry Pi):** menjalankan *broker* MQTT lokal, menampung data saat internet ke *cloud* putus (*store-and-forward*), dan yang terpenting menjalankan aturan darurat (kenaikan ≥ 15 cm/10 menit → sirene hilir) secara lokal sehingga peringatan tetap jalan tanpa internet dan target < 3 detik tercapai. |
| 3. Lapisan Pemrosesan & Data | Mengapa *publish/subscribe* (MQTT) dan basis data *time-series* lebih tepat dibanding HTTP *polling* dan RDBMS biasa pada kasus ini? | **MQTT:** data didorong begitu tersedia tanpa menunggu siklus *polling*; *header* minimal 2 byte jauh lebih hemat daripada *header* HTTP ratusan byte; QoS 1 menjamin pesan peringatan sampai, *retained message* memberi status terakhir pada dasbor baru, LWT mendeteksi pos yang mati; satu pesan diterima banyak pihak sekaligus (dasbor, bot Telegram, sirene). **Time-series DB:** penulisan berfrekuensi tinggi (5 pos × 3 sensor, naik 6 kali saat darurat), kompresi, retensi, dan *downsampling* bawaan; kueri "kenaikan 10 menit terakhir" jauh lebih ringan daripada pada tabel RDBMS yang terus membengkak. |
| 4. Lapisan Aplikasi | Informasi visual apa yang wajib tampil di dasbor BPBD vs notifikasi warga? Bagaimana logika deteksi kenaikan cepat (≥ 15 cm/10 menit)? | **Dasbor BPBD:** peta lima pos berwarna status, grafik tinggi muka air dan hujan per pos, laju kenaikan cm/10 menit, status koneksi dan baterai, log peringatan, tombol uji sirene. **Notifikasi warga:** satu pesan singkat tanpa grafik, misalnya "SIAGA BANJIR: air di Pos Hulu 2 naik 18 cm dalam 10 menit, siapkan evakuasi." **Logika:** *ring buffer* 10 menit per pos; Δh = h(sekarang) − min(h 10 menit terakhir); bila Δh ≥ 15 cm bertahan pada dua pembacaan berturut-turut, status naik ke SIAGA, perintah interval 10 detik dikirim ke pos, sirene hilir dinyalakan, dan notifikasi dikirim. Status turun hanya setelah kondisi normal bertahan beberapa menit. |
| 5. Lapisan Bisnis & Lintas-Lapis Keamanan | Apa risiko jika topik MQTT perintah sirene tidak diamankan (tanpa TLS/ACL)? Siapa saja pemangku kepentingan yang terlibat? | **Risiko:** pemalsuan perintah sirene tengah malam sehingga warga panik lalu tidak percaya lagi pada sirene; sirene dimatikan saat banjir sungguhan; data disadap karena tanpa enkripsi; *broker* dibanjiri pesan (DoS). **Mitigasi:** TLS port 8883, autentikasi per perangkat, ACL agar hanya *gateway* boleh *publish* ke topik sirene, dan validasi perintah terhadap data sensor. **Pemangku kepentingan:** BPBD Provinsi dan Kota Bengkulu, BWS Sumatera VII, pemerintah desa/kelurahan hulu dan hilir, warga bantaran sungai, Diskominfo, BMKG, serta tim pengembang dan pemelihara alat. |

## Bagian 2 — Jawaban Problem Set Minggu 1 (Level C1–C6)

> **Soal 1 [C1 – Remember]** Sebutkan secara berurutan lima lapisan pada model arsitektur 5-lapis IoT serta enam sudut pandang arsitektur (*architectural views*) yang didefinisikan dalam standar internasional ISO/IEC 30141:2024!

| No | Lima Lapisan Arsitektur IoT | Enam *Architectural Views* ISO/IEC 30141:2024 |
|---|---|---|
| 1 | Lapisan Persepsi (*Perception/Device*) | *Usage View*: aktor, peran, dan skenario penggunaan |
| 2 | Lapisan Transpor & Edge (*Network & Edge*) | *Functional View*: dekomposisi fungsi penginderaan, komunikasi, pemrosesan, penyimpanan, keamanan |
| 3 | Lapisan Pemrosesan, *Middleware* & Data | *Information View*: struktur data, metadata, format *payload*, aliran informasi |
| 4 | Lapisan Aplikasi & Visualisasi | *Communication View*: tumpukan protokol antara jaringan terbatas dan internet |
| 5 | Lapisan Bisnis & Tata Kelola | *System/Deployment View*: penempatan perangkat dan kontainer di *node*, *edge*, *cloud* |
| 6 | | *Construction View* (baru di edisi 2024): pola desain praktis implementasi IoT |

> **Soal 2 [C2 – Understand]** Jelaskan perbedaan mendasar antara sistem M2M tradisional dan IoT modern ditinjau dari: (a) protokol komunikasi dan keterbukaan jaringan, (b) interoperabilitas data, serta (c) skalabilitas integrasi aplikasi! Berikan masing-masing satu contoh nyata.

| Aspek | M2M Tradisional | IoT Modern |
|---|---|---|
| (a) Protokol & keterbukaan jaringan | Titik-ke-titik tertutup lewat SMS, GPRS, atau serial dengan protokol milik vendor. Contoh: meter listrik yang mengirim angka meteran lewat SMS ke satu server PLN. | Berbasis IP terbuka dengan protokol standar (MQTT, CoAP, HTTP), perangkat lintas vendor bicara ke *broker* yang sama. Contoh: ESP32 pemantau tinggi air yang *publish* MQTT ke Mosquitto. |
| (b) Interoperabilitas data | Data terkunci di sistem vendor (*silo*) dengan format biner atau teks milik vendor. Contoh: data SCADA pabrik yang hanya terbaca perangkat lunak pembuatnya. | Format standar (JSON/CBOR) yang dapat diambil lewat REST API. Contoh: data SIARENG dibaca dasbor, bot Telegram, dan aplikasi BPBD sekaligus. |
| (c) Skalabilitas integrasi aplikasi | Setiap aplikasi atau perangkat baru memerlukan koneksi dan integrasi khusus. Contoh: menghubungkan sistem meter SMS ke aplikasi baru butuh pengembangan khusus. | Aplikasi baru cukup *subscribe* ke topik yang ada tanpa mengubah perangkat. Contoh: notifikasi Telegram sistem banjir ditambahkan sebagai satu layanan *subscriber* baru. |

> **Soal 3 [C3 – Apply]** Petakan delapan komponen sistem pemantauan suhu ruang server Gedung Dekanat FT UNIB (BME280, ESP32, Wi-Fi kampus, Mosquitto, FastAPI, InfluxDB, Grafana, sertifikat TLS X.509) ke model referensi ITU-T Y.4000/Y.2060 beserta fungsinya!

| No | Komponen | Lapisan / Kapabilitas ITU-T Y.4000 | Fungsi |
|---|---|---|---|
| 1 | Sensor BME280 | *Device Layer* | Mengukur suhu, kelembapan, dan tekanan ruang server |
| 2 | Mikrokontroler ESP32 | *Device Layer* (kapabilitas *device* dan *gateway* langsung) | Membaca sensor via I2C, mengemas JSON, mengirim lewat Wi-Fi |
| 3 | Jaringan Wi-Fi kampus | *Network Layer* | Akses dan transportasi IP dari perangkat ke server |
| 4 | *Broker* Eclipse Mosquitto | *Service Support & Application Support Layer* | Perantara pesan *publish/subscribe* telemetri |
| 5 | Layanan Python FastAPI | *Service Support & Application Support Layer* | *Ingestion*, validasi, dan penyediaan REST API |
| 6 | Basis data InfluxDB | *Service Support & Application Support Layer* | Penyimpanan deret waktu suhu dan kelembapan |
| 7 | Panel Grafana | *Application Layer* | Visualisasi dan peringatan untuk admin ruang server |
| 8 | Sertifikat TLS X.509 | *Security Capabilities* (vertikal, lintas lapisan) | Autentikasi perangkat/server dan enkripsi kanal MQTT dan HTTPS |

> **Soal 4 [C4 – Analyze]** Analisislah dampak buruk apabila `delay(2000)` tetap digunakan ketika simpul ESP32 juga harus mempertahankan koneksi *keep-alive* MQTT dan merespons perintah darurat mematikan relai dari server secara instan!

Selama `delay(2000)`, `loop()` berhenti total sehingga tiga hal terganggu:

1. **MQTT tidak dilayani.** Pustaka seperti PubSubClient hanya bekerja saat `client.loop()` dipanggil. Selama *delay*, ESP32 tidak mengirim PINGREQ dan tidak membaca paket masuk. Bila *keep-alive* pendek atau *delay* lain menumpuk, *broker* menganggap klien mati, memutus koneksi, dan memublikasikan LWT "offline"; perangkat lalu sibuk menyambung ulang dan data selama itu dapat hilang.
2. **Perintah darurat tertunda.** Pesan "matikan relai" menumpuk di buffer TCP dan baru diproses setelah `delay()` selesai, terlambat hingga 2 detik. Untuk aktuator berbahaya seperti pompa, pemanas, atau sirene, keterlambatan ini dapat menimbulkan kerusakan fisik, dan pesan bisa terbuang bila buffer penuh.
3. **Input lokal ikut tertahan**, seperti tombol yang tidak terdeteksi pada Eksperimen 3 praktikum.

Solusinya adalah pola `millis()` atau *task* FreeRTOS dengan `client.loop()` dipanggil sesering mungkin.

> **Soal 5 [C5 – Evaluate]** Evaluasilah usulan 200 titik sensor kualitas udara di mana setiap ESP32 terhubung langsung ke MySQL di *cloud* melalui internet publik tanpa *edge gateway* maupun *message broker*, dari aspek (a) keamanan jaringan, (b) efisiensi koneksi dan daya, serta (c) ketahanan terhadap putusnya jaringan!

| Aspek | Kelemahan Rancangan | Perbaikan yang Diusulkan |
|---|---|---|
| (a) Keamanan jaringan | Port MySQL 3306 terbuka ke internet dan menjadi target *brute-force*. Kredensial basis data tersimpan di 200 perangkat: satu perangkat dicuri dan *flash*-nya dibaca, seluruh basis data terbuka termasuk hak hapus tabel. Koneksi MySQL dari ESP32 jarang memakai TLS. | Perangkat hanya berbicara ke *broker*/API dengan identitas masing-masing (sertifikat atau token per perangkat, ACL per topik). Basis data hanya diakses dari jaringan internal oleh layanan *ingestion*. |
| (b) Efisiensi koneksi & daya | Setiap data memerlukan *handshake* TCP, autentikasi, dan kueri SQL. 200 koneksi bersamaan membebani `max_connections`. Radio ESP32 aktif lebih lama sehingga boros baterai. | MQTT dengan *header* 2 byte dan satu koneksi persisten per perangkat; penulisan ke basis data dilakukan berkelompok oleh satu layanan. |
| (c) Ketahanan jaringan | Saat internet atau MySQL mati, data hilang karena tidak ada penampung. Perubahan skema tabel memaksa pembaruan firmware 200 perangkat. | *Edge gateway* atau *broker* dengan QoS 1, *persistent session*, dan *buffer* lokal (*store-and-forward*); skema data dipisahkan dari perangkat lewat lapisan *ingestion*. |

Kesimpulan: rancangan tersebut tidak layak untuk produksi dan memerlukan lapisan *broker*, idealnya juga *gateway*, di antara perangkat dan basis data.

> **Soal 6 [C6 – Create]** Rancanglah diagram blok arsitektur 5-lapis beserta *software stack* dan contoh *payload* JSON untuk "Smart Cold-Chain Pemantauan Suhu Ruang Penyimpanan Ikan di Pelabuhan Pulau Baai Bengkulu". Sertakan mekanisme menjaga keutuhan data saat kapal/truk pendingin berada di area tanpa sinyal selama 30 menit!

| Lapisan | Rancangan *Software Stack* |
|---|---|
| 5. Bisnis | KPI persentase waktu suhu dalam batas dan kerugian ikan rusak; kepatuhan HACCP; UU PDP untuk data lokasi sopir |
| 4. Aplikasi | Dasbor Grafana (suhu per kontainer, posisi truk, lama pintu terbuka), peringatan Telegram bila suhu > −18 °C (beku) atau > 4 °C (dingin) lebih dari 10 menit, laporan rantai dingin per pengiriman |
| 3. Pemrosesan & Data | Mosquitto (TLS 8883, ACL per perangkat) → *ingestion* FastAPI (validasi Pydantic) → TimescaleDB/InfluxDB (data mentah 90 hari, rata-rata per jam untuk audit) |
| 2. Transpor & Edge | Gudang: Wi-Fi ke Raspberry Pi *gateway* (Mosquitto lokal + penampung SQLite). Truk/kapal: modem LTE-M/NB-IoT dengan MQTT QoS 1 ke *cloud* |
| 1. Persepsi | ESP32 per ruang/truk, dua sensor DS18B20 tahan air, sensor pintu (*reed switch*, interupsi), GPS NEO-6M di truk, buzzer alarm lokal |

```
{
  "device_id": "truk-bkl-07",
  "seq": 18342,
  "ts": "2026-11-12T03:14:05Z",
  "temp_c": [-19.4, -18.9],
  "door_open": false,
  "gps": { "lat": -3.8954, "lon": 102.2713 },
  "batt_v": 3.94,
  "buffered": false
}
```
Listing 1: Contoh *payload* JSON simpul *Smart Cold-Chain*

Mekanisme keutuhan data selama 30 menit tanpa sinyal:

1. Setiap pembacaan diberi `seq` berurutan dan stempel waktu dari RTC atau GPS, bukan waktu server, sehingga urutan dan waktu aslinya tetap benar.
2. Bila publikasi gagal, pesan ditulis ke *ring buffer* di flash (LittleFS). Pada interval 1 menit, 30 menit setara 30 × ~150 byte ≈ 4,5 KB, sehingga kapasitas buffer dapat disiapkan untuk berjam-jam.
3. Alarm suhu tetap berjalan lokal melalui buzzer di kabin, tidak bergantung pada sinyal.
4. Saat tersambung kembali, isi buffer dikirim dari yang terlama dengan QoS 1 dan tanda `"buffered": true`; pesan dihapus dari buffer hanya setelah PUBACK diterima.
5. Server memakai pasangan `(device_id, seq)` sebagai kunci unik, sehingga pengiriman ulang tidak menghasilkan data ganda dan celah `seq` menandai data yang benar-benar hilang.
