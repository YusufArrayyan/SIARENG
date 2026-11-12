# Panduan membuat SIARENG dari nol

Panduan ini untuk kamu yang belum pernah merakit alat IoT. Ikuti dari Langkah 1 sampai selesai, satu per satu. Setiap langkah ditutup dengan bagian **"Berhasil kalau"**. Jangan lanjut sebelum tanda itu terlihat, supaya kalau ada masalah kamu tahu persis di langkah mana penyebabnya.

Langkah 1 sampai 3 tidak butuh alat sama sekali, jadi bisa dikerjakan sambil menunggu kiriman komponen.

| Langkah | Yang dikerjakan | Butuh alat? | Perkiraan waktu |
|---|---|---|---|
| 1 | Siapkan laptop | Tidak | 1 jam |
| 2 | Ambil kode SIARENG | Tidak | 5 menit |
| 3 | Coba simulasi dan dashboard demo | Tidak | 30 menit |
| 4 | Beli komponen | | menunggu kiriman |
| 5 | Rakit di breadboard, satu komponen per tahap | Ya | 2–3 jam |
| 6 | Kalibrasi sensor | Ya | 30 menit |
| 7 | Sambungkan ke dashboard lewat kabel USB | Ya | 15 menit |
| 8 | Kirim data lewat WiFi (alat bebas dari laptop) | Ya | 30 menit |
| 9 | Peringatan ke Telegram (opsional) | Ya | 20 menit |
| 10 | Pasang di lapangan | Ya | lihat panduan perakitan |

> SIARENG adalah alat pembelajaran. Ambang statusnya masih nilai awal untuk uji, bukan hasil kajian geologi, dan alat ini bukan sistem peringatan dini resmi.

---

## Cara kerja SIARENG dalam satu gambar

```
   DI LERENG                                  DI LAPTOP / SERVER                DI MANA SAJA
+----------------------+   kabel USB     +--------------------------+      +-------------------+
| Sensor tanah  ──┐    |   atau WiFi     |  backend-api (Python)    |      | Dashboard browser |
| Sensor hujan  ──┼─► ESP32 ───────────► |  terima, simpan, siarkan | ───► | laptop atau HP    |
| MPU6050       ──┘    |                 |                          | ───► | Telegram (opsi)   |
|   LED + buzzer ◄─────|                 +--------------------------+      +-------------------+
+----------------------+
```

1. **Tiga sensor** mengukur kelembapan tanah, hujan, dan pergeseran kemiringan.
2. **ESP32** (komputer mini) membaca sensor 5 kali per detik, lalu memutuskan status: aman, waspada, atau bahaya.
3. **LED dan buzzer** memberi peringatan langsung di lokasi. Bagian ini tetap bekerja walaupun internet mati.
4. ESP32 juga mengirim datanya ke **backend** di laptop. Backend menyimpan data dan meneruskannya ke **dashboard**, yaitu halaman web yang kamu pantau.

### Kenali komponennya

| Komponen | Tugasnya | Bayangkan sebagai |
|---|---|---|
| ESP32 | Membaca sensor, memutuskan status, mengirim data | Otak alat |
| MPU6050 (GY-521) | Mengukur kemiringan terhadap gravitasi | Waterpas digital |
| Sensor tanah kapasitif | Mengukur seberapa basah tanah | Jari yang ditancap ke tanah |
| Sensor hujan | Mendeteksi air di permukaan panel | Telapak tangan yang menadah hujan |
| LED hijau, kuning, merah | Menunjukkan status | Lampu lalu lintas |
| Buzzer | Bunyi peringatan | Peluit |
| Tombol | Menetapkan posisi sekarang sebagai "normal" | Tombol reset timbangan |
| Breadboard dan kabel jumper | Menyambung komponen tanpa solder | Papan colok |

### Aturan status

| Status | Syarat | Yang terjadi di alat |
|---|---|---|
| Aman | Selain kondisi di bawah | LED hijau |
| Waspada | Tanah jenuh (≥ 80%), atau lereng bergeser ≥ 2°, atau tanah basah (≥ 60%) saat hujan deras (≥ 40%) | LED kuning, bip tiap 3 detik |
| Bahaya | Tanah jenuh (≥ 80%) dan lereng bergeser ≥ 5° | LED merah berkedip, buzzer terus berbunyi |

Status naik hanya kalau kondisinya bertahan 2 detik, dan turun kalau sudah bertahan 6 detik. Jeda ini mencegah alarm palsu saat sensor tersenggol sebentar.

---

## Langkah 1: Siapkan laptop

Pasang empat program ini. Semuanya gratis.

1. **Visual Studio Code**: https://code.visualstudio.com
2. **Git**: https://git-scm.com (di Windows, biarkan semua pilihan bawaan saat memasang)
3. **Python 3.10 atau lebih baru**: https://www.python.org/downloads (di Windows, centang **"Add python.exe to PATH"** di layar pertama)
4. Di dalam VS Code, buka menu Extensions (`Ctrl+Shift+X`), lalu pasang:
   - **PlatformIO IDE**. Tunggu sampai tulisan "Installing PlatformIO Core" di pojok bawah hilang. Ini bisa makan 5–10 menit.
   - **Wokwi Simulator**. Setelah terpasang, tekan `F1`, ketik `Wokwi: Request a New License`, dan ikuti halaman yang terbuka di browser.

**Berhasil kalau:** di bilah kiri VS Code muncul ikon kepala semut (PlatformIO), dan perintah berikut menampilkan nomor versi di terminal:

```bash
git --version
```

```bash
python --version
```

## Langkah 2: Ambil kode SIARENG

Buka terminal (di VS Code: menu Terminal → New Terminal), pindah ke folder tempat kamu ingin menyimpan proyek, lalu jalankan:

```bash
git clone https://github.com/YusufArrayyan/SIARENG.git
```

Isi folder `SIARENG` yang perlu kamu tahu:

| Folder | Isi |
|---|---|
| `firmware/` | Program yang ditanam ke ESP32 |
| `dashboard/` | Halaman web pemantau |
| `backend-api/` | Program Python penghubung ESP32 dan dashboard |
| `docs/` | Panduan, RAB, dan laporan |
| `labs/` | Tugas praktikum |

**Berhasil kalau:** folder `SIARENG` muncul dan berisi folder-folder di atas.

## Langkah 3: Coba tanpa alat

### 3a. Simulasi alat di Wokwi

1. Di VS Code, pilih File → Open Folder, lalu buka folder **`SIARENG/firmware`** (bukan folder `SIARENG`).
2. Klik ikon PlatformIO → **Build**. Proses pertama cukup lama karena mengunduh perkakas ESP32.
3. Tekan `F1` → `Wokwi: Start Simulator`.
4. Putar potensiometer dan geser slider MPU6050 sesuai skenario di [`simulasi-demo.md`](simulasi-demo.md).

**Berhasil kalau:** LED hijau menyala di simulasi, dan saat tanah dibuat jenuh sambil kemiringan digeser, LED merah berkedip.

### 3b. Dashboard mode demo

Buka file `SIARENG/dashboard/index.html` dengan klik dua kali. Di bagian "Kendali demo", tekan **Lereng bergerak**.

**Berhasil kalau:** setelah 2 detik, panel besar berubah menjadi "Bahaya" dan muncul banner merah. Sekarang kamu sudah tahu tampilan akhir sistemnya.

## Langkah 4: Beli komponen

Pakai daftar di [`RAB_SIARENG_hemat.xlsx`](RAB_SIARENG_hemat.xlsx), sekitar Rp210.000 termasuk ongkir. Setiap baris sudah berisi link toko dan varian yang harus dipilih.

Kamu juga butuh **kabel data micro USB** (sudah ada di RAB) dan **laptop**. Solder belum diperlukan untuk tahap uji.

## Langkah 5: Rakit di breadboard

Kunci supaya tidak bingung: **pasang satu komponen, uji, baru pasang berikutnya.** Kalau semua dipasang sekaligus lalu ada yang salah, sulit mencari penyebabnya.

### Yang perlu dipahami dulu

- **Breadboard:** lubang dalam satu baris pendek (5 lubang) saling tersambung. Dua jalur panjang di pinggir (bertanda merah `+` dan biru `−`) tersambung sepanjang papan, dan dipakai untuk membagi daya.
- **Label pin ESP32:** tulisan di papan bisa `D21`, `G21`, `IO21`, atau `21`. Semuanya berarti **GPIO 21**.
- **Cabut kabel USB setiap kali mengubah sambungan.** Kabel yang salah colok saat alat menyala bisa merusak komponen.
- **Semua sensor diberi daya dari pin `3V3`, jangan dari `VIN` atau `5V`.**

### 5.1 ESP32 saja

1. Tancapkan ESP32 di breadboard, melintang di atas celah tengah. Kalau papanmu versi lebar (38 pin) sehingga satu sisi tidak menyisakan lubang, tidak apa-apa: pin di sisi itu disambung dengan kabel jumper **male-female** langsung ke kaki ESP32.
2. Sambungkan pin `3V3` ke jalur merah, dan pin `GND` ke jalur biru.
3. Buka `firmware/include/config.h`, ubah `#define SIMULASI 1` menjadi `0`.
4. Colokkan kabel USB ke laptop. Di VS Code (folder `firmware` terbuka), klik PlatformIO → **Upload**.
5. Kalau upload berhenti di tulisan `Connecting.....`, tahan tombol **BOOT** di ESP32 sampai proses berjalan.
6. Klik PlatformIO → **Monitor**.

**Berhasil kalau:** di Monitor muncul baris `{"event":"boot",...}` lalu `{"event":"error","msg":"MPU6050 tidak terdeteksi..."}`. Pesan error itu wajar karena sensornya memang belum dipasang.

Kalau port tidak ditemukan sama sekali, pasang driver USB-nya. Lihat tulisan pada chip kecil di dekat port USB ESP32: **CP2102** (cari "CP210x driver Silicon Labs") atau **CH340** (cari "CH340 driver").

### 5.2 MPU6050 (kemiringan)

| Pin MPU6050 | Ke |
|---|---|
| VCC | jalur merah (3V3) |
| GND | jalur biru (GND) |
| SDA | GPIO 21 |
| SCL | GPIO 22 |

Colok USB lagi, lalu tekan tombol **EN** (atau RST) di ESP32 untuk memulai ulang.

**Berhasil kalau:** pesan error hilang, muncul `{"event":"baseline_siap"}`, lalu baris data tiap 2 detik. Miringkan breadboard: nilai `tilt_delta_deg` naik.

### 5.3 Tiga LED

Untuk setiap LED: kaki **panjang** ke resistor (220 Ω atau 330 Ω), ujung resistor lainnya ke GPIO. Kaki **pendek** ke jalur biru (GND).

| LED | GPIO |
|---|---|
| Hijau | 26 |
| Kuning | 27 |
| Merah | 14 |

**Berhasil kalau:** setelah restart, LED kuning menyala 2 detik (alat sedang mengambil patokan kemiringan), lalu berganti hijau. Miringkan breadboard lebih dari 2°: setelah 2 detik LED kuning menyala.

### 5.4 Buzzer

| Pin buzzer | Ke |
|---|---|
| S atau I/O (sinyal) | GPIO 25 |
| − atau GND | jalur biru |
| + atau VCC (kalau ada) | jalur merah |

**Berhasil kalau:** saat status waspada (breadboard dimiringkan), terdengar bip pendek tiap 3 detik.

### 5.5 Tombol kalibrasi

Tancapkan tombol melintang di celah tengah breadboard. Satu kaki ke GPIO 15, kaki di sisi diagonalnya ke jalur biru (GND).

**Berhasil kalau:** saat ditekan, Monitor menampilkan `{"event":"kalibrasi_ulang"}`, dan posisi miring saat itu dianggap normal (LED kembali hijau).

### 5.6 Sensor tanah

| Pin sensor | Ke |
|---|---|
| VCC | jalur merah |
| GND | jalur biru |
| AOUT | GPIO 34 |

**Berhasil kalau:** nilai `soil_raw` berubah saat bagian bawah sensor digenggam atau dicelup ke air. Celup hanya sampai garis batas di badan sensor.

### 5.7 Sensor hujan

Sensor ini terdiri atas dua bagian: panel bergaris dan modul kecil. Sambungkan panel ke modul dengan dua kabel pendek bawaannya, lalu:

| Pin modul | Ke |
|---|---|
| VCC | jalur merah |
| GND | jalur biru |
| AO | GPIO 35 |
| DO | tidak dipakai |

**Berhasil kalau:** nilai `rain_raw` turun saat panel ditetesi air.

Setelah ketujuh tahap ini lolos, rangkaianmu lengkap.

## Langkah 6: Kalibrasi sensor

Setiap sensor sedikit berbeda, jadi alat perlu tahu angka "kering" dan "basah" milik sensormu. Lihat nilai `soil_raw` dan `rain_raw` di Monitor.

| Yang diukur | Caranya | Isi ke `config.h` |
|---|---|---|
| Tanah kering | Sensor dibiarkan di udara | `SOIL_RAW_KERING` |
| Tanah basah | Sensor dicelup air sampai garis batas | `SOIL_RAW_BASAH` |
| Hujan kering | Panel dilap sampai kering | `RAIN_RAW_KERING` |
| Hujan basah | Seluruh panel dibasahi | `RAIN_RAW_BASAH` |

Isi empat angka itu di blok `#else` (bagian "NILAI CONTOH untuk sensor asli") pada `firmware/include/config.h`, lalu Upload lagi.

**Berhasil kalau:** `soil_pct` mendekati 0 di udara dan mendekati 100 di air. Lalu jalankan skenario bahaya: celup sensor tanah, miringkan breadboard lebih dari 5°, dan tunggu 2 detik. LED merah harus berkedip dan buzzer berbunyi.

## Langkah 7: Sambungkan ke dashboard lewat kabel USB

Siapkan backend, cukup sekali. Buka terminal di folder `SIARENG/backend-api`:

```bash
python -m venv .venv
```

```bash
.venv/Scripts/pip install -r requirements.txt
```

Cari nomor port ESP32: di Windows buka Device Manager → Ports (COM & LPT), misalnya `COM5`. **Tutup Monitor PlatformIO** karena satu port hanya bisa dipakai satu program. Lalu jalankan backend.

Di Git Bash:

```bash
SERIAL_PORT=COM5 .venv/Scripts/python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Di PowerShell:

```powershell
$env:SERIAL_PORT="COM5"; .venv\Scripts\python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Buka http://localhost:8000 di browser.

**Berhasil kalau:** di pojok kanan atas dashboard tertulis "Menerima data dari alat", dan angka di layar ikut berubah saat sensor dibasahi atau breadboard dimiringkan.

## Langkah 8: Kirim data lewat WiFi

Dengan WiFi, alat tidak perlu menempel ke laptop. Cukup beri daya (adaptor atau powerbank), dan datanya terkirim sendiri.

Syaratnya: ESP32 dan laptop tersambung ke **WiFi yang sama**, dan WiFi itu **2,4 GHz** (ESP32 tidak bisa 5 GHz). Hotspot HP bisa dipakai.

1. Cari alamat IP laptop. Jalankan perintah ini, lalu catat angka di baris "IPv4 Address", misalnya `192.168.1.10`:

   ```bash
   ipconfig
   ```

2. Di folder `firmware/include/`, salin `secrets.example.h` menjadi `secrets.h`, lalu isi:

   ```cpp
   #define WIFI_SSID  "nama WiFi kamu"
   #define WIFI_PASS  "kata sandi WiFi"
   #define SERVER_URL "http://192.168.1.10:8000/api/telemetry"
   #define API_KEY    ""
   ```

   File `secrets.h` tidak ikut ter-commit ke GitHub, jadi kata sandi WiFi tidak tersebar.

3. Di `config.h`, ubah `#define KIRIM_WIFI 0` menjadi `1`, lalu Upload.
4. Jalankan backend seperti di Langkah 7. Tanpa kabel USB, bagian `SERIAL_PORT=COM5` boleh dihapus.
5. Saat pertama dijalankan, Windows akan bertanya soal firewall. Pilih **Allow access**.

**Berhasil kalau:** di Monitor muncul `{"event":"wifi","ip":"..."}`, dan dashboard tetap menerima data setelah kabel USB dicabut dan ESP32 diberi daya dari adaptor atau powerbank. Kolom "Sinyal WiFi" di dashboard menampilkan kekuatan sinyal.

Dashboard juga bisa dibuka dari HP di WiFi yang sama: `http://192.168.1.10:8000` (pakai IP laptopmu).

Kalau WiFi putus, LED dan buzzer di alat tetap bekerja. Dashboard akan menampilkan "Tidak ada data" setelah 15 detik, supaya kamu tidak mengira lereng aman padahal alatnya mati.

### Kunci API (disarankan)

Supaya server hanya menerima data dari alatmu, pasang kata kunci yang sama di dua tempat:

- di `secrets.h`: `#define API_KEY "kunci-rahasia-kamu"`, lalu Upload ulang;
- saat menjalankan backend, tambahkan `API_KEY=kunci-rahasia-kamu` di depan perintah (Git Bash), atau `$env:API_KEY="kunci-rahasia-kamu";` (PowerShell).

## Langkah 9: Peringatan ke Telegram (opsional)

Backend bisa mengirim pesan Telegram setiap kali status berubah, dan saat alat berhenti mengirim data lebih dari 60 detik.

1. Di Telegram, buka **@BotFather**, kirim `/newbot`, ikuti petunjuknya, dan simpan **token** yang diberikan. Perlakukan token ini seperti kata sandi.
2. Kirim pesan apa saja ke bot barumu.
3. Buka alamat ini di browser (ganti `TOKEN`), lalu cari angka setelah `"chat":{"id":`. Itu **chat ID** kamu.

   ```
   https://api.telegram.org/botTOKEN/getUpdates
   ```

4. Jalankan backend dengan dua pengaturan tambahan. Di Git Bash:

   ```bash
   TELEGRAM_BOT_TOKEN=token-kamu TELEGRAM_CHAT_ID=123456789 .venv/Scripts/python -m uvicorn app:app --host 0.0.0.0 --port 8000
   ```

**Berhasil kalau:** saat kamu memicu status waspada di alat, pesan masuk ke Telegram dalam beberapa detik.

## Langkah 10: Pasang di lapangan

Setelah semuanya bekerja di meja, lanjutkan ke [`panduan-perakitan.md`](panduan-perakitan.md). Panduan itu membahas pemindahan ke PCB, catu daya panel surya, box tahan air, dan pemasangan di lereng.

Satu hal yang perlu dipikirkan sejak sekarang: di lereng, alat butuh WiFi untuk mengirim data. Pilihannya router atau modem 4G di dekat lokasi, atau hotspot HP yang ditinggal. Kalau lokasinya tanpa sinyal sama sekali, alat tetap berfungsi sebagai alarm lokal lewat LED dan buzzer.

---

## Kalau ada masalah

| Gejala | Penyebab yang paling sering | Cara mengatasi |
|---|---|---|
| Upload berhenti di `Connecting.....` | ESP32 belum masuk mode upload | Tahan tombol BOOT sampai upload berjalan |
| Port COM tidak muncul | Driver belum terpasang, atau kabelnya hanya kabel cas | Pasang driver CP210x atau CH340. Coba kabel lain |
| `MPU6050 tidak terdeteksi` | SDA dan SCL tertukar, atau kabel longgar | SDA ke GPIO 21, SCL ke GPIO 22, VCC ke 3V3 |
| LED tidak menyala | LED terbalik | Kaki panjang ke resistor, kaki pendek ke GND |
| `soil_raw` atau `rain_raw` tidak berubah | Kabel AOUT/AO salah pin | Tanah ke GPIO 34, hujan ke GPIO 35 |
| Angka persen terbalik (basah = 0%) | Nilai kering dan basah tertukar di `config.h` | Tukar kedua angka itu |
| Status langsung waspada padahal alat diam | Patokan kemiringan diambil saat alat masih bergerak | Diamkan alat, lalu tekan tombol kalibrasi |
| Backend: `could not open port` | Port masih dipakai Monitor PlatformIO, atau nomor port salah | Tutup Monitor. Cek nomor port di Device Manager |
| Dashboard: "Alat tidak mengirim data" | ESP32 belum tersambung ke backend | USB: cek `SERIAL_PORT`. WiFi: cek `SERVER_URL` dan firewall |
| Monitor: `{"event":"kirim_gagal","http":-1}` | ESP32 tidak bisa menjangkau laptop | Pastikan WiFi sama, IP di `SERVER_URL` benar, backend berjalan dengan `--host 0.0.0.0` |
| Monitor: `"http":401` | Kunci API tidak sama | Samakan `API_KEY` di `secrets.h` dan di perintah backend |
| Tidak pernah muncul `{"event":"wifi"...}` | Nama atau kata sandi WiFi salah, atau WiFi 5 GHz | Periksa `secrets.h`. Pakai jaringan 2,4 GHz |

## Kamus singkat

| Istilah | Arti |
|---|---|
| Firmware | Program yang ditanam di dalam ESP32 |
| Upload / flash | Mengirim firmware dari laptop ke ESP32 |
| GPIO | Kaki ESP32 yang bisa dipakai untuk membaca atau mengendalikan sesuatu |
| ADC | Bagian ESP32 yang mengubah tegangan sensor menjadi angka 0–4095 |
| I2C | Cara komunikasi dua kabel (SDA dan SCL) yang dipakai MPU6050 |
| Serial Monitor | Jendela untuk membaca teks yang dikirim ESP32 lewat USB |
| JSON | Format teks data, contoh: `{"status":"aman","soil_pct":20}` |
| Backend | Program di laptop atau server yang menerima dan menyimpan data |
| Dashboard | Halaman web untuk memantau data |
| Telemetri | Data pengukuran yang dikirim alat secara berkala |
| Kalibrasi | Menyesuaikan pembacaan alat dengan kondisi sebenarnya |
