# Tugas Minggu 1: LK-1 (Kasus A) dan Problem Set Modul C1–C6

Proyek: SIARENG (Siaga Lereng)
Tugas Praktikum Minggu 1 (tabel blocking vs non-blocking dan C1–C6 praktikum) ada di [`laporan-minggu-01.md`](laporan-minggu-01.md). Dokumen ini berisi dua tugas lain dari Bahan Ajar Minggu 1:

1. **LK-1**: analisis arsitektur Kasus A, peringatan dini banjir DAS Air Bengkulu (bobot 1%).
2. **Problem Set modul C1–C6**: soal belajar mandiri. Soalnya berbeda dengan pertanyaan di panduan praktikum.

---

## Bagian A. LK-1: Analisis Arsitektur Kasus A

**Ringkasan kasus:** ada 5 pos pantau dari hulu (Bengkulu Tengah) sampai muara (Rawa Makmur, Tanjung Agung). Setiap pos mengukur tinggi muka air, curah hujan, dan kecepatan arus setiap 1 menit. Dua pos hulu hanya punya panel surya dan sinyal seluler yang naik turun. Jika air naik ≥ 15 cm dalam 10 menit, sistem harus mempercepat pengiriman menjadi tiap 10 detik, membunyikan sirene di hilir, dan memberi peringatan ke BPBD serta warga dalam waktu kurang dari 3 detik.

| Lapisan | Pertanyaan panduan | Hasil pemetaan dan justifikasi |
|---|---|---|
| **1. Persepsi** | Sensor dan aktuator apa di hulu dan hilir? Mengapa hulu perlu *deep sleep*? | **Hulu:** sensor ultrasonik/radar tinggi muka air (JSN-SR04T tahan air, atau radar level untuk akurasi), penakar hujan tipe *tipping bucket* (keluaran pulsa, dibaca lewat interupsi), sensor kecepatan arus (*flow* tipe baling-baling atau radar permukaan), ESP32, panel surya + baterai Li-Ion/LiFePO4. **Hilir:** sensor yang sama ditambah **sirene** 12 V (lewat relai/MOSFET) dan lampu strobo. **Alasan *deep sleep* di hulu:** daya hanya dari panel surya. ESP32 yang terus menyala dengan radio aktif menarik ~120 mA dan menghabiskan baterai 3000 mAh dalam sekitar 20 jam, apalagi saat musim hujan yang mendung berhari-hari. Dengan pola bangun tiap 1 menit untuk mengukur lalu tidur, arus rata-rata turun ke orde 1–3 mA. Penakar hujan tetap terhitung karena pulsa *tipping bucket* bisa membangunkan ESP32 (EXT0) atau dihitung oleh koprosesor ULP. |
| **2. Transpor dan edge** | Konektivitas apa untuk hulu vs kota? Apa peran *edge gateway* saat internet putus? | **Hulu:** sinyal seluler tidak andal, jadi pilihan utama **LoRa/LoRaWAN AS923-2** ke *gateway* di titik yang punya listrik dan internet (kantor desa atau pos tengah). Jangkauannya 2–15 km dengan daya sangat rendah. Modem 4G/NB-IoT dipakai sebagai cadangan bila ada sinyal. **Pos kota/hilir:** Wi-Fi atau 4G, karena ada listrik PLN. **Peran *edge gateway* (Raspberry Pi):** menjalankan *broker* MQTT lokal, menampung data saat internet ke *cloud* putus (*store-and-forward*), lalu mengirim ulang saat tersambung. Yang paling penting: aturan darurat (air naik ≥ 15 cm/10 menit → nyalakan sirene hilir) **dijalankan di gateway**, tidak menunggu *cloud*. Peringatan lokal tetap berjalan walaupun internet mati, dan target < 3 detik lebih mudah dicapai. |
| **3. Pemrosesan dan data** | Mengapa MQTT dan *time-series DB* lebih tepat daripada HTTP *polling* + RDBMS? | **MQTT (*publish/subscribe*):** pesan langsung didorong (*push*) begitu ada data, tidak menunggu siklus *polling*. *Header* MQTT minimal 2 byte, jauh lebih kecil daripada *header* HTTP yang ratusan byte, sehingga hemat kuota dan daya. Ada QoS 1 agar pesan peringatan pasti sampai, *retained message* agar dasbor baru langsung tahu status terakhir, dan LWT agar pos yang mati terdeteksi otomatis. Satu pesan bisa diterima banyak pihak sekaligus (dasbor BPBD, bot Telegram, sirene) tanpa pengirim tahu siapa saja penerimanya. **Time-series DB (InfluxDB/TimescaleDB):** data sensor berupa deret waktu yang ditulis terus-menerus (5 pos × 3 sensor × 1 per menit, dan 6 kali lipat saat darurat). TSDB dioptimalkan untuk tulis cepat, kompresi, kebijakan retensi, dan *downsampling* (misalnya data per menit disimpan 30 hari, rata-rata per jam disimpan bertahun-tahun). Kueri seperti "kenaikan dalam 10 menit terakhir" juga jauh lebih ringan dibanding tabel RDBMS biasa yang terus membengkak. |
| **4. Aplikasi** | Apa yang tampil di dasbor BPBD vs notifikasi warga? Bagaimana logika deteksi kenaikan cepat? | **Dasbor BPBD:** peta 5 pos dengan warna status, grafik tinggi muka air dan hujan per pos, laju kenaikan (cm per 10 menit), status koneksi dan baterai setiap pos, log peringatan, serta tombol uji sirene. **Notifikasi warga (Telegram):** satu pesan singkat dan jelas, misalnya "SIAGA BANJIR: air di Pos Hulu 2 naik 18 cm dalam 10 menit. Perkiraan tiba di Rawa Makmur sekitar 2 jam. Siapkan evakuasi.", tanpa grafik teknis. **Logika deteksi:** simpan *ring buffer* pembacaan 10 menit terakhir per pos. Hitung `Δh = h(sekarang) − min(h dalam 10 menit terakhir)`. Jika `Δh ≥ 15 cm` dan kondisinya bertahan pada 2 pembacaan berturut-turut (agar satu bacaan ultrasonik yang meleset tidak memicu alarm), naikkan status ke SIAGA. Kirim perintah interval 10 detik ke pos (*downlink*), nyalakan sirene hilir, dan kirim notifikasi. Status turun hanya setelah kondisi normal bertahan beberapa menit (histeresis waktu). |
| **5. Bisnis dan keamanan lintas lapis** | Apa risikonya jika topik MQTT sirene tidak diamankan? Siapa pemangku kepentingannya? | **Risiko tanpa TLS/ACL:** siapa pun di jaringan bisa (1) **memalsukan** pesan ke topik sirene sehingga sirene berbunyi tengah malam dan warga panik, lalu lama-lama tidak percaya lagi pada sirene (*cry wolf*); (2) **mematikan** sirene saat banjir sungguhan terjadi; (3) **menyadap** data, karena tanpa TLS isi pesan bisa dibaca; (4) membanjiri *broker* dengan pesan (DoS). Mitigasi: TLS di port 8883, autentikasi per perangkat, ACL agar hanya *gateway* yang boleh *publish* ke `.../sirene/cmd`, dan pemeriksaan bahwa perintah sirene konsisten dengan data sensor. **Pemangku kepentingan:** BPBD Provinsi dan Kota Bengkulu (operator dan pengambil keputusan), BWS Sumatera VII (pengelola sungai), pemerintah desa/kelurahan di hulu dan hilir, warga bantaran sungai, Diskominfo (jaringan dan data), BMKG (data hujan pembanding), serta tim pengembang dan pemelihara alat. |

---

## Bagian B. Problem Set Modul Minggu 1

### Soal 1 [C1]. Lima lapisan dan enam *views*

**Lima lapisan model arsitektur IoT (dari bawah ke atas):**

1. Lapisan Persepsi (*Perception/Device*): sensor, aktuator, mikrokontroler.
2. Lapisan Transpor/Jaringan dan Edge (*Network & Edge*): Wi-Fi, LoRaWAN, NB-IoT, *gateway*, protokol MQTT/CoAP/HTTP.
3. Lapisan Pemrosesan/*Middleware* dan Data (*Processing & Storage*): *broker*, API, basis data, *rule engine*.
4. Lapisan Aplikasi dan Visualisasi (*Application*): dasbor, peringatan, analitik.
5. Lapisan Bisnis (*Business*): KPI, kebijakan, kepatuhan regulasi, tata kelola.

**Enam *architectural views* ISO/IEC 30141:2024:**

1. *Usage View*: aktor, peran, dan skenario penggunaan.
2. *Functional View*: dekomposisi fungsi penginderaan, komunikasi, pemrosesan, penyimpanan, dan keamanan.
3. *Information View*: struktur data, metadata perangkat, format *payload*, aliran informasi.
4. *Communication View*: tumpukan protokol antara jaringan terbatas dan internet.
5. *System/Deployment View*: penempatan perangkat keras dan kontainer di *node*, *edge*, *cloud*.
6. *Construction View* (baru di edisi 2024): pola desain praktis untuk membangun sistem IoT.

### Soal 2 [C2]. M2M vs IoT

| Aspek | M2M tradisional | IoT modern |
|---|---|---|
| (a) Protokol dan keterbukaan jaringan | Titik-ke-titik tertutup lewat SMS, GPRS, atau serial, sering dengan protokol milik vendor. **Contoh:** meter listrik yang mengirim angka meteran lewat SMS ke satu server PLN. | Berbasis IP terbuka dengan protokol standar (MQTT, CoAP, HTTP). Perangkat dari vendor berbeda bisa berbicara ke *broker* yang sama. **Contoh:** sensor tinggi air ESP32 yang mengirim MQTT ke Mosquitto. |
| (b) Interoperabilitas data | Data terkunci di sistem vendor (*silo*), dengan format biner atau teks milik vendor. **Contoh:** data SCADA pabrik yang hanya terbaca oleh perangkat lunak pembuatnya. | Data dalam format standar (JSON/CBOR) yang bisa diambil lewat REST API dan dipakai aplikasi lain. **Contoh:** data cuaca SIARENG bisa dibaca dasbor, bot Telegram, dan aplikasi BPBD sekaligus. |
| (c) Skalabilitas integrasi aplikasi | Menambah aplikasi atau perangkat berarti menambah koneksi atau integrasi khusus satu per satu. **Contoh:** menghubungkan sistem meter SMS ke aplikasi baru butuh pengembangan khusus. | Pola *publish/subscribe* dan API memungkinkan aplikasi baru cukup *subscribe* ke topik yang ada tanpa mengubah perangkat. **Contoh:** menambah notifikasi Telegram ke sistem banjir cukup dengan satu layanan baru yang *subscribe* ke topik peringatan. |

### Soal 3 [C3]. Pemetaan 8 komponen ruang server FT UNIB ke ITU-T Y.4000/Y.2060

ITU-T Y.4000 terdiri atas 4 lapisan horizontal ditambah 2 kapabilitas vertikal (manajemen dan keamanan).

| No | Komponen | Lapisan/kapabilitas Y.4000 | Fungsi |
|---|---|---|---|
| 1 | Sensor BME280 | *Device Layer* | Mengukur suhu, kelembapan, dan tekanan ruang server |
| 2 | Mikrokontroler ESP32 | *Device Layer* (kapabilitas *device* dan *gateway* langsung) | Membaca sensor lewat I2C, mengemas JSON, mengirim lewat Wi-Fi |
| 3 | Jaringan Wi-Fi kampus | *Network Layer* | Akses dan transportasi IP dari perangkat ke server |
| 4 | *Broker* Eclipse Mosquitto | *Service Support & Application Support Layer* | Perantara pesan *publish/subscribe* untuk telemetri |
| 5 | Layanan Python FastAPI | *Service Support & Application Support Layer* | *Ingestion*, validasi, dan penyediaan REST API |
| 6 | Basis data InfluxDB | *Service Support & Application Support Layer* (penyimpanan generik) | Menyimpan deret waktu suhu dan kelembapan |
| 7 | Panel Grafana | *Application Layer* | Visualisasi dan peringatan untuk admin ruang server |
| 8 | Sertifikat TLS X.509 | *Security Capabilities* (vertikal, lintas lapisan) | Autentikasi perangkat/server dan enkripsi kanal MQTT dan HTTPS |

### Soal 4 [C4]. Dampak `delay(2000)` pada MQTT *keep-alive* dan perintah darurat

Selama `delay(2000)`, `loop()` berhenti total. Akibatnya:

1. **MQTT tidak dilayani.** Pustaka seperti PubSubClient hanya bekerja saat `client.loop()` dipanggil. Selama *delay*, ESP32 tidak mengirim PINGREQ dan tidak membaca paket masuk. Jika *keep-alive* diset pendek (misalnya 5 detik) dan ada *delay* lain yang menumpuk, atau proses baca sensor ikut lambat, *broker* menganggap klien mati, memutus koneksi, dan memublikasikan LWT "offline". Perangkat lalu sibuk menyambung ulang, dan data selama itu bisa hilang.
2. **Perintah darurat tertunda.** Pesan "matikan relai" dari server menumpuk di buffer TCP dan baru diproses setelah `delay()` selesai, jadi bisa terlambat sampai 2 detik. Untuk aktuator berbahaya (pompa, pemanas, sirene), keterlambatan ini bisa menimbulkan kerusakan fisik. Jika buffer penuh, pesan bahkan bisa terbuang.
3. **Respons tombol dan interupsi logika ikut tertahan**, seperti yang terlihat di Eksperimen 3 praktikum.

Solusinya: pola `millis()` atau *task* FreeRTOS, dengan `client.loop()` dipanggil sesering mungkin.

### Soal 5 [C5]. Kritik arsitektur 200 ESP32 yang langsung menulis ke MySQL publik

| Aspek | Masalah | Perbaikan |
|---|---|---|
| (a) Keamanan jaringan | Port MySQL (3306) harus dibuka ke internet, sehingga menjadi target *brute-force* dan eksploitasi. Kredensial basis data tersimpan di 200 perangkat. Satu perangkat dicuri dan *flash*-nya dibaca, seluruh basis data terbuka, termasuk hak hapus tabel. Protokol MySQL di ESP32 juga jarang memakai TLS. | Perangkat hanya boleh bicara ke *broker*/API dengan identitas masing-masing (sertifikat atau token per perangkat, ACL per topik). Basis data hanya bisa diakses dari jaringan internal oleh layanan *ingestion*. |
| (b) Efisiensi koneksi dan daya | Protokol MySQL berat: *handshake* TCP + autentikasi + kueri SQL untuk setiap data. 200 koneksi bersamaan membebani batas `max_connections` server. Di ESP32, waktu radio aktif lebih lama, jadi lebih boros baterai. | MQTT dengan *header* 2 byte dan satu koneksi persisten per perangkat. *Broker* dirancang untuk ribuan klien, dan penulisan ke basis data dilakukan berkelompok (*batch*) oleh satu layanan. |
| (c) Ketahanan terhadap jaringan putus | Jika internet atau MySQL mati, data hilang karena tidak ada penampung. Setiap perangkat harus punya logika *retry* sendiri. Perubahan skema tabel memaksa *update firmware* 200 perangkat. | *Edge gateway* atau *broker* dengan QoS 1, *persistent session*, dan *buffer* lokal di perangkat atau gateway (*store-and-forward*). Skema data dipisahkan dari perangkat lewat lapisan *ingestion*. |

Kesimpulan: rancangan ini tidak layak untuk produksi. Perlu ditambahkan lapisan *broker* (dan idealnya *gateway*) di antara perangkat dan basis data.

### Soal 6 [C6]. Rancangan *Smart Cold-Chain* Pelabuhan Pulau Baai

**Arsitektur 5 lapisan:**

| Lapisan | Isi |
|---|---|
| 1. Persepsi | ESP32 di tiap ruang pendingin dan truk/kapal: sensor suhu DS18B20 tahan air (2 titik per ruang), sensor pintu (*reed switch*, interupsi), GPS NEO-6M di truk, buzzer lokal untuk alarm suhu. |
| 2. Transpor dan edge | Ruang pendingin di pelabuhan: Wi-Fi ke **Raspberry Pi gateway** (Mosquitto lokal + penampung SQLite). Truk/kapal: modem **LTE-M/NB-IoT** + MQTT (QoS 1) langsung ke *cloud*. |
| 3. Pemrosesan dan data | Mosquitto (TLS 8883, ACL per perangkat) → layanan *ingestion* FastAPI (validasi Pydantic) → **TimescaleDB**/InfluxDB (retensi data mentah 90 hari, rata-rata per jam selamanya untuk audit mutu). |
| 4. Aplikasi | Dasbor Grafana (suhu per kontainer, posisi truk di peta, lama pintu terbuka), peringatan Telegram ke pengawas bila suhu > −18 °C (beku) atau > 4 °C (dingin) lebih dari 10 menit, laporan rantai dingin per pengiriman (PDF) untuk pembeli. |
| 5. Bisnis | KPI: persentase waktu suhu dalam batas, kerugian ikan rusak. Kepatuhan: standar penanganan ikan (HACCP), UU PDP untuk data lokasi sopir. |

**Contoh *payload* JSON:**

```json
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

**Mekanisme saat 30 menit tanpa sinyal:**

1. Setiap pembacaan diberi `seq` berurutan dan stempel waktu dari RTC atau GPS (bukan waktu server), jadi urutan dan waktu aslinya tetap benar.
2. Jika publikasi gagal, pesan ditulis ke *ring buffer* di flash (LittleFS) atau ke PSRAM. Pada interval 1 menit, 30 menit berarti 30 pesan × ~150 byte ≈ 4,5 KB. Kecil, kapasitas buffer bisa disiapkan untuk berjam-jam.
3. Alarm suhu tetap berjalan lokal (buzzer di kabin sopir), tidak bergantung pada sinyal.
4. Saat tersambung lagi, perangkat mengirim isi buffer dari yang terlama dengan QoS 1 dan tanda `"buffered": true`, sebelum melanjutkan data baru. Pesan dihapus dari buffer hanya setelah PUBACK diterima.
5. Server memakai `(device_id, seq)` sebagai kunci unik, jadi pesan yang terkirim ulang tidak tersimpan dua kali, dan celah `seq` yang tersisa menandai data yang benar-benar hilang.
