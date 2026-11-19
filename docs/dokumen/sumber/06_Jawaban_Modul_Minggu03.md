---
berkas: Jawaban_Modul_Minggu03_SIARENG
jenis: LEMBAR JAWABAN
unit: PRODI S1 | INFORMATIKA | Jurusan Teknik Informatika | Fakultas Teknik UNIB
judul: LEMBAR JAWABAN MINGGU KE-3
subjudul: Problem Set Firmware ESP32, I2C/SPI, FreeRTOS, & Deep Sleep
kolom: Minggu=3 dari 16 | Kelompok=SIARENG | Sub-CPMK=Sub-CPMK 2.1
kepala_kiri: Lembar Jawaban Minggu 3 — Teknologi IoT
kepala_kanan: Modul 2: Firmware, I2C/SPI, FreeRTOS & Deep Sleep
kaki: Kelompok SIARENG · Kurikulum OBE — Standar SN-Dikti & LAM Infokom
---

> **Capaian Pembelajaran Minggu Ke-3 (Sub-CPMK 2.1 — Level C3, P3)**
> Mahasiswa mampu memprogram ESP32 untuk akuisisi data multi-sensor melalui antarmuka GPIO/ADC/I2C/SPI secara *non-blocking* dan hemat daya.
> Dokumen ini memuat jawaban **Problem Set Minggu 3** level C1–C6. Soal C6 dikerjakan sebagai firmware utuh di `labs/minggu-03-c6-longsor/` dan telah berhasil dikompilasi.

| No | Peran Rekayasa | Nama Anggota | NPM |
|---|---|---|---|
| 1 | Device & Firmware Engineer | ........................................ | .................... |
| 2 | Back-End & Data Engineer | ........................................ | .................... |
| 3 | Security & DevOps Engineer | ........................................ | .................... |
| 4 | Dashboard Engineer & Project Manager | ........................................ | .................... |

## Bagian 1 — Jawaban Soal C1–C3

> **Soal 1 [C1 – Remember]** (a) Sebutkan fungsi masing-masing jalur sinyal pada bus I2C dan SPI! (b) Berapakah alamat I2C baku untuk sensor BME280 dan layar OLED SSD1306? (c) Sebutkan lima mode daya ESP32 dari arus terbesar hingga terkecil!

| Bus | Jalur | Fungsi |
|---|---|---|
| I2C | SDA | Data dua arah, *open-drain* |
| I2C | SCL | *Clock* dari master |
| SPI | MOSI | Data dari master ke slave |
| SPI | MISO | Data dari slave ke master |
| SPI | SCK | *Clock* dari master |
| SPI | CS/SS | Memilih slave aktif (aktif LOW), satu pin per slave |

(b) BME280 beralamat `0x76` bila SDO ke GND atau `0x77` bila SDO ke VCC; OLED SSD1306 beralamat `0x3C` (sebagian modul `0x3D`).
(c) Urutan arus terbesar ke terkecil: Active (80–240 mA), Modem Sleep (20–30 mA), Light Sleep (0,8–2 mA), Deep Sleep (10–150 µA), Power Down lewat pin EN (~5 µA).

> **Soal 2 [C2 – Understand]** (a) Mengapa bus I2C memakai konfigurasi *open-drain* dan membutuhkan resistor *pull-up* eksternal? Apa yang terjadi bila *pull-up* tidak terpasang? (b) Jelaskan perbedaan siklus eksekusi program saat ESP32 bangun dari *Light Sleep* dibandingkan dari *Deep Sleep*!

(a) Banyak peranti berbagi kabel SDA dan SCL yang sama. Bila setiap peranti boleh menarik jalur ke HIGH dan LOW secara aktif, dua peranti yang menulis bersamaan dapat terhubung singkat. Dengan *open-drain*, peranti hanya menarik jalur ke LOW atau melepasnya, sedangkan level HIGH dibentuk resistor *pull-up* 2,2–4,7 kΩ. Akibatnya "LOW selalu menang" dengan aman, yang sekaligus dipakai untuk arbitrase multi-master dan *clock stretching*. Tanpa *pull-up*, jalur mengambang setelah dilepas, level tidak pernah kembali HIGH dengan jelas, transaksi gagal (NACK atau *timeout*), dan I2C Scanner tidak menemukan peranti. Banyak modul *breakout* sudah membawa *pull-up* sendiri, sehingga masalah ini sering baru muncul saat memakai chip tanpa modul.

(b) Pada *Light Sleep*, *clock* CPU dijeda tetapi RAM dan register tetap berdaya, sehingga saat bangun eksekusi **melanjutkan baris setelah** `esp_light_sleep_start()` dengan seluruh variabel utuh. Pada *Deep Sleep*, CPU dan RAM utama padam; saat bangun ESP32 **reboot**, `setup()` dijalankan dari awal, variabel global kembali ke nilai awal, dan hanya isi `RTC_DATA_ATTR` yang tersisa.

> **Soal 3 [C3 – Apply]** (a) Stasiun cuaca di lereng Gunung Patah mencatat tekanan 895,2 hPa. Dengan P<sub>0</sub> = 1013,25 hPa, hitunglah estimasi ketinggian stasiun! (b) Jika simpul bertenaga Li-Ion 2500 mAh (η = 0,85), aktif 2 detik (90 mA) dan tidur *Deep Sleep* 10 menit (30 µA), hitunglah I<sub>avg</sub> dan masa pakai baterai dalam hari!

| Besaran | Perhitungan | Hasil |
|---|---|---|
| Rasio tekanan | P / P<sub>0</sub> = 895,2 / 1013,25 | 0,88349 |
| Pangkat 1/5,255 | 0,88349<sup>0,19029</sup> | 0,97670 |
| (a) Ketinggian | h = 44330 × (1 − 0,97670) | ≈ 1033 m dpl |
| Arus rata-rata | I<sub>avg</sub> = (90 × 2 + 0,03 × 598) / 600 = (180 + 17,94) / 600 | ≈ 0,330 mA |
| (b) Masa pakai | T = 2500 × 0,85 / 0,330 | ≈ 6441 jam ≈ 268 hari |

Ketinggian (a) merupakan perkiraan karena rumus mengasumsikan atmosfer standar; perbedaan tekanan permukaan laut harian beberapa hPa setara sekitar 8–9 m per hPa.

## Bagian 2 — Jawaban Soal C4–C5

> **Soal 4 [C4 – Analyze]** Animasi OLED yang rumit di `loop()` membuat pembacaan sensor tersendat dan interupsi tombol terlewat, sedangkan `int counter = 0;` selalu kembali 0 setiap bangun dari *Deep Sleep*. Analisislah dua kelemahan tersebut dan berikan solusi kode menggunakan FreeRTOS dan memori RTC!

**Kelemahan 1: animasi OLED memblokir `loop()`.** Setiap `display.display()` mengirim 1024 byte lewat I2C (25–30 ms pada 400 kHz). Animasi yang memanggilnya berkali-kali membuat satu putaran `loop()` memakan ratusan milidetik, sehingga sensor tidak terbaca dan penekanan tombol yang dicek dengan *polling* terlewat. Solusinya memindahkan tampilan ke *task* FreeRTOS terpisah dengan lajunya sendiri dan mengubah tombol menjadi interupsi.

```
volatile bool flagTombol = false;
void IRAM_ATTR isrTombol() { flagTombol = true; }       // tidak pernah terlewat

SemaphoreHandle_t mutexI2C;                              // OLED dan sensor berbagi bus Wire

void TaskOled(void*) {
  for (;;) {
    xSemaphoreTake(mutexI2C, portMAX_DELAY);
    gambarAnimasi();
    display.display();
    xSemaphoreGive(mutexI2C);
    vTaskDelay(pdMS_TO_TICKS(100));   // 10 fps, CPU dilepas antarbingkai
  }
}

void setup() {
  mutexI2C = xSemaphoreCreateMutex();
  attachInterrupt(digitalPinToInterrupt(15), isrTombol, FALLING);
  xTaskCreatePinnedToCore(TaskOled, "oled", 4096, nullptr, 1, nullptr, 0);
}

void loop() {
  if (flagTombol) { flagTombol = false; tanganiTombol(); }
  xSemaphoreTake(mutexI2C, portMAX_DELAY);
  bacaSensor();
  xSemaphoreGive(mutexI2C);
  vTaskDelay(pdMS_TO_TICKS(200));
}
```
Listing 1: Pemisahan *task* tampilan, interupsi tombol, dan *mutex* bus I2C

**Kelemahan 2: pencacah hilang setelah Deep Sleep.** Variabel `counter` berada di SRAM yang padam selama Deep Sleep, dan program dijalankan ulang dari awal setiap bangun. Solusinya menempatkan variabel di memori RTC; bila nilai harus bertahan sampai daya dicabut, simpan juga ke NVS dengan `Preferences`.

```
RTC_DATA_ATTR int counter = 0;   // diisi 0 hanya saat power-on, bertahan saat Deep Sleep
void setup() { counter++; /* baca, kirim */ esp_deep_sleep_start(); }
```
Listing 2: Pencacah persisten di RTC Slow Memory

> **Soal 5 [C5 – Evaluate]** Empat sensor akselerometer I2C identik beralamat tunggal `0x68` tanpa pin pengubah alamat akan dipasang pada satu bus. Evaluasilah kelayakannya dan bandingkan tiga solusi: (1) I2C Multiplexer TCA9548A, (2) *Software Bit-Banged I2C*, (3) antarmuka I2C ganda `Wire` dan `Wire1`!

Memasang keempat sensor pada satu bus **tidak layak**: keempatnya menjawab alamat yang sama secara bersamaan, data bertabrakan, dan master tidak dapat memilih sensor tertentu.

| Kriteria | (1) Multiplexer TCA9548A | (2) Software Bit-Banged I2C | (3) `Wire` + `Wire1` |
|---|---|---|---|
| Menampung 4 sensor | Ya, 8 kanal per chip | Ya, satu pasang pin per bus | Tidak, ESP32 hanya punya 2 kontroler I2C |
| Kecepatan & beban CPU | 400 kHz penuh, hanya tambahan perintah pilih kanal | Lambat (~50–100 kHz), CPU sibuk, *jitter* tinggi | Kecepatan penuh, ditangani perangkat keras |
| Kebutuhan GPIO | 2 pin | 8 pin | 4 pin |
| Biaya | +1 modul (±Rp20–35 ribu) | Gratis | Gratis |
| Kesesuaian untuk pemantauan getaran | Baik | Kurang, *jitter* mengganggu analisis | Hanya untuk 2 sensor |

Rekomendasi kelompok: **TCA9548A**, satu-satunya opsi yang menampung keempat sensor pada kecepatan penuh dengan beban CPU kecil. Untuk sensor yang memiliki pin AD0 seperti MPU6050, kombinasi opsi (3) dengan alamat alternatif `0x69` dapat menampung empat sensor tanpa multiplexer, namun soal menyatakan sensornya tidak memiliki pin pengubah alamat.

## Bagian 3 — Jawaban Soal C6: Smart Early-Warning Landslide Node

> **Soal 6 [C6 – Create]** Rancanglah *state machine* dan program C++ lengkap yang mengintegrasikan: (a) pembacaan BME280 via I2C setiap 15 menit dengan *Timer Deep Sleep*, (b) sensor getaran yang memicu *EXT0 Wakeup* bila terjadi guncangan sebelum jadwal timer, (c) penyimpanan 10 riwayat tekanan terakhir di `RTC_DATA_ATTR` untuk menghitung tren, dan (d) pengaktifan sinyal darurat bila tekanan turun ≥ 3 hPa dalam 1 jam!

```
  [BANGUN] -> [TENTUKAN PEMICU] -> [BACA BME280] -> [SIMPAN RIWAYAT RTC] -> [EVALUASI TREN]
   power-on / timer / getaran                                                     |
                                       turun >= 3 hPa per jam? --ya--> [ALARM 10 dtk]
                                                       | tidak                 |
                                                       v                       v
                                                  [LAPOR JSON]  <--------------+
                                                       |
                         [ATUR PEMICU: timer 15 menit + EXT0 getaran]  ->  [DEEP SLEEP]
```
Listing 3: *State machine* simpul peringatan dini longsor

| Kebutuhan | Implementasi pada `labs/minggu-03-c6-longsor/src/main.cpp` |
|---|---|
| (a) BME280 tiap 15 menit via Timer Deep Sleep | `esp_sleep_enable_timer_wakeup(15 × 60 × 10⁶ µs)`; BME280 dibaca dalam *forced mode* lalu sensor tidur kembali |
| (b) Sensor getaran via EXT0 | SW-420 DO di GPIO 33 (RTC GPIO), `esp_sleep_enable_ext0_wakeup(GPIO_NUM_33, 1)`; jumlah getaran dicatat di `RTC_DATA_ATTR`. EXT0 tidak dipasang bila sensor masih bergetar saat akan tidur, agar ESP32 tidak bangun berulang tanpa henti |
| (c) 10 riwayat tekanan di RTC | *Ring buffer* `RTC_DATA_ATTR Sampel riwayat[10]` berisi `{detik, tekanan}`; waktu dari `gettimeofday()` karena jam RTC tetap berjalan selama Deep Sleep |
| (d) Darurat bila turun ≥ 3 hPa dalam 1 jam | `penurunanSatuJam()` mencari selisih terbesar terhadap semua sampel 3600 detik terakhir, tetap benar walau sampel tidak berjarak sama; bila ≥ 3 hPa buzzer GPIO 25 dan LED GPIO 26 berkedip 10 detik |

```
float penurunanSatuJam(uint32_t tNow, float pNow) {
  float maksTurun = 0.0f;
  for (int i = 0; i < jumlahSampel; i++) {
    const Sampel& s = riwayat[i];
    if (tNow - s.t <= JENDELA_TREN_S && s.t < tNow) {
      maksTurun = max(maksTurun, s.tekananHpa - pNow);
    }
  }
  return maksTurun;
}
```
Listing 4: Perhitungan penurunan tekanan dalam jendela 1 jam dari riwayat RTC

Contoh keluaran JSON saat kondisi darurat:

```
{"device_id":"esp32-longsor-node01","cycle":9,"wakeup":"timer","t_s":7201,"sensor_ok":true,
 "temp_c":24.81,"hum_pct":93.2,"pressure_hpa":896.40,"drop_1h_hpa":3.12,
 "vibration_count":2,"history_n":9,"alert":true,"alert_reason":"pressure_drop"}
```
Listing 5: *Payload* telemetri simpul longsor

Catatan rekayasa kelompok:

- Penurunan tekanan udara menandakan cuaca memburuk, bukan longsor itu sendiri. Pada sistem SIARENG, sinyal ini sebaiknya dikombinasikan dengan kelembapan tanah dan pergeseran kemiringan, bukan dipakai sendirian sebagai alarm longsor.
- Satu-satunya `delay()` berada pada fase alarm, dan itu disengaja karena perangkat langsung tidur setelahnya sehingga tidak ada tugas lain yang tertahan.
- Perangkat aktif sekitar 1 detik per 15 menit, sehingga arus rata-rata berada pada orde 0,1–0,2 mA dan sesuai untuk baterai dengan panel surya kecil.
