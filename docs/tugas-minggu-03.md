# Tugas Minggu 3: Problem Set Modul C1–C6

Proyek: SIARENG (Siaga Lereng)
Laporan praktikum Lab-2 ada di [`laporan-lab02-minggu-03.md`](laporan-lab02-minggu-03.md). Dokumen ini menjawab Problem Set Bahan Ajar Minggu 3. Soal C6 (*Smart Early-Warning Landslide Node*) dikerjakan sebagai firmware utuh di [`labs/minggu-03-c6-longsor/`](../labs/minggu-03-c6-longsor/), dan firmware itu sudah berhasil dikompilasi.

---

### Soal 1 [C1]

**(a) Fungsi jalur sinyal**

| Bus | Jalur | Fungsi |
|---|---|---|
| I2C | SDA | Data dua arah (*open-drain*) |
| | SCL | *Clock* dari master |
| SPI | MOSI | Data dari master ke slave |
| | MISO | Data dari slave ke master |
| | SCK | *Clock* dari master |
| | CS/SS | Memilih slave yang aktif (aktif LOW), satu pin per slave |

**(b) Alamat I2C baku:** BME280 `0x76` (pin SDO ke GND) atau `0x77` (SDO ke VCC). OLED SSD1306 `0x3C` (beberapa modul `0x3D`).

**(c) Mode daya ESP32 dari arus terbesar ke terkecil:**

1. Active (80–240 mA)
2. Modem Sleep (20–30 mA)
3. Light Sleep (0,8–2 mA)
4. Deep Sleep (10–150 µA)
5. Power Down / Hibernation lewat pin EN (~5 µA)

### Soal 2 [C2]

**(a) Mengapa I2C *open-drain* dan butuh *pull-up*.** Di bus I2C banyak peranti berbagi kabel yang sama. Jika setiap peranti boleh menarik jalur ke HIGH dan LOW secara aktif, dua peranti yang menulis bersamaan bisa saling hubung singkat (satu menarik ke 3,3 V, yang lain ke 0 V). Dengan *open-drain*, peranti hanya bisa menarik jalur ke LOW atau melepasnya. Level HIGH dibuat oleh resistor *pull-up* (2,2–4,7 kΩ). Akibatnya "LOW menang" dengan aman, dan mekanisme ini sekaligus dipakai untuk arbitrase multi-master dan *clock stretching*.

Jika *pull-up* tidak terpasang, jalur SDA/SCL mengambang. Begitu peranti melepas jalur, level tidak pernah kembali ke HIGH dengan jelas, sehingga sinyal terbaca acak, transaksi gagal (NACK atau *timeout*), dan I2C Scanner tidak menemukan peranti apa pun. Catatan: banyak modul breakout sudah membawa resistor *pull-up* sendiri, jadi masalah ini sering baru muncul saat memakai chip tanpa modul.

**(b) Light Sleep vs Deep Sleep.** Pada **Light Sleep**, *clock* CPU dihentikan, tetapi RAM dan register tetap berdaya. Saat bangun, eksekusi **melanjutkan baris tepat setelah** `esp_light_sleep_start()`, dan semua variabel masih utuh. Pada **Deep Sleep**, CPU dan RAM utama dimatikan. Saat bangun, ESP32 **reboot**: `setup()` dijalankan lagi dari awal, variabel global kembali ke nilai awal, dan hanya isi memori RTC (`RTC_DATA_ATTR`) yang tersisa. Karena itu program Deep Sleep perlu dirancang sebagai urutan "bangun, kerjakan, tidur" di dalam `setup()`.

### Soal 3 [C3]

**(a) Ketinggian stasiun di lereng Gunung Patah (P = 895,2 hPa, P₀ = 1013,25 hPa):**

```
h = 44330 × [1 − (P / P0)^(1/5,255)]
  = 44330 × [1 − (895,2 / 1013,25)^0,19029]
  = 44330 × [1 − 0,88349^0,19029]
  = 44330 × (1 − 0,97670)
  ≈ 1033 m di atas permukaan laut
```

Angka ini perkiraan, karena rumus mengasumsikan atmosfer standar. Tekanan permukaan laut harian di Bengkulu bisa berbeda beberapa hPa, dan setiap 1 hPa setara dengan sekitar 8–9 m.

**(b) Arus rata-rata dan umur baterai (2500 mAh, η = 0,85):** t<sub>aktif</sub> = 2 s pada 90 mA, t<sub>tidur</sub> = 598 s pada 30 µA.

```
I_avg = (90 × 2 + 0,03 × 598) / 600 = (180 + 17,94) / 600 ≈ 0,330 mA
T     = 2500 × 0,85 / 0,330 ≈ 6441 jam ≈ 268 hari (≈ 8,8 bulan)
```

### Soal 4 [C4]. Dua kelemahan arsitektur perangkat lunak

**Kelemahan 1: animasi OLED di `loop()` memblokir sensor dan tombol.** Setiap `display.display()` mengirim 1024 byte lewat I2C (25–30 ms pada 400 kHz). Animasi rumit memanggilnya berkali-kali, sehingga satu putaran `loop()` bisa makan ratusan milidetik. Selama itu sensor tidak dibaca dan penekanan tombol yang dicek dengan polling terlewat.

Perbaikan: pindahkan tampilan ke task FreeRTOS terpisah dengan laju sendiri, dan ubah tombol menjadi interupsi.

```cpp
volatile bool flagTombol = false;
void IRAM_ATTR isrTombol() { flagTombol = true; }   // tidak pernah terlewat

SemaphoreHandle_t mutexI2C;                          // OLED dan sensor berbagi bus Wire

void TaskOled(void*) {
  for (;;) {
    xSemaphoreTake(mutexI2C, portMAX_DELAY);
    gambarAnimasi();
    display.display();
    xSemaphoreGive(mutexI2C);
    vTaskDelay(pdMS_TO_TICKS(100));                  // 10 fps, CPU dilepas di antara bingkai
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

**Kelemahan 2: `int counter = 0;` selalu kembali ke 0 setelah Deep Sleep.** Variabel itu berada di SRAM, yang mati saat Deep Sleep, dan setiap bangun program dijalankan ulang dari awal. Perbaikan: simpan di memori RTC.

```cpp
RTC_DATA_ATTR int counter = 0;   // diinisialisasi hanya saat power-on, bertahan saat Deep Sleep
void setup() { counter++; /* ... */ esp_deep_sleep_start(); }
```

Jika nilai harus bertahan sampai daya benar-benar dicabut, simpan juga ke NVS memakai `Preferences`.

### Soal 5 [C5]. Empat akselerometer I2C beralamat sama (`0x68`)

Memasang keempatnya di satu bus **tidak layak**. Keempat sensor menjawab di alamat yang sama secara bersamaan, data bertabrakan, dan master tidak bisa memilih sensor mana yang diajak bicara.

| Kriteria | (1) Multiplexer TCA9548A | (2) I2C perangkat lunak (*bit-bang*) | (3) `Wire` + `Wire1` (I2C perangkat keras ganda) |
|---|---|---|---|
| Bisa menampung 4 sensor | Ya, 8 kanal (bisa sampai 64 dengan 8 mux) | Ya, satu pasang pin per bus | **Tidak**: ESP32 hanya punya 2 kontroler I2C, jadi maksimal 2 sensor beralamat sama |
| Kecepatan dan beban CPU | Kecepatan penuh 400 kHz, hanya ada tambahan perintah pilih kanal | Lambat (~50–100 kHz), CPU sibuk menggoyang pin, jitter tinggi | Kecepatan penuh, ditangani perangkat keras |
| Pin GPIO | 2 pin saja | 2 pin per sensor (8 pin) | 4 pin |
| Biaya dan komponen | +1 modul (~Rp20–35 ribu) | Gratis | Gratis |
| Cocok untuk pemantauan gempa (sampling cepat, sinkron) | **Baik** | Kurang, karena jitter mengganggu analisis getaran | Hanya bila sensornya 2 |

Rekomendasi: **TCA9548A**. Ini satu-satunya opsi yang menampung keempat sensor pada kecepatan penuh dengan beban CPU kecil. Kompromi praktisnya: gabungkan (3) dan alamat alternatif. MPU6050 punya pin AD0 untuk berpindah ke `0x69`, jadi `Wire` dan `Wire1` masing-masing bisa membawa dua sensor (`0x68` dan `0x69`) tanpa mux. Namun soal menyebut sensornya tidak punya pin pengubah alamat, sehingga TCA9548A tetap pilihan utama.

### Soal 6 [C6]. *Smart Early-Warning Landslide Node*

**Mesin keadaan perangkat lunak:**

```
            ┌───────────────────────────────────────────────────────────────┐
            ▼                                                               │
   [BANGUN] → [TENTUKAN PEMICU] → [BACA BME280] → [SIMPAN RIWAYAT RTC] → [EVALUASI TREN]
     power-on / timer / getaran                                             │
                                                    turun ≥ 3 hPa/jam? ──ya──→ [ALARM 10 dtk]
                                                            │ tidak               │
                                                            ▼                     ▼
                                                        [LAPOR JSON] ←────────────┘
                                                            │
                                     [ATUR PEMICU: timer 15 mnt + EXT0 getaran] → [DEEP SLEEP]
```

**Cara setiap kebutuhan dipenuhi** ([`labs/minggu-03-c6-longsor/src/main.cpp`](../labs/minggu-03-c6-longsor/src/main.cpp)):

| Kebutuhan | Implementasi |
|---|---|
| (a) Baca BME280 tiap 15 menit lewat Timer Deep Sleep | `esp_sleep_enable_timer_wakeup(15 × 60 × 10⁶ µs)`. BME280 dibaca dalam *forced mode* (sekali ukur lalu sensor tidur lagi), sehingga hemat daya. |
| (b) Sensor getaran membangunkan lebih awal lewat EXT0 | SW-420 DO di **GPIO 33** (RTC GPIO), `esp_sleep_enable_ext0_wakeup(GPIO_NUM_33, 1)`. Getaran dihitung di `RTC_DATA_ATTR jumlahGetaran` dan dilaporkan dengan `alert_reason: "vibration"`. EXT0 tidak dipasang jika sensor masih bergetar saat akan tidur, supaya ESP32 tidak bangun-tidur berulang tanpa henti. |
| (c) 10 riwayat tekanan di memori RTC | *Ring buffer* `RTC_DATA_ATTR Sampel riwayat[10]` berisi `{detik, tekanan}`. Waktu diambil dari `gettimeofday()`, karena jam RTC ESP32 tetap berjalan selama Deep Sleep. |
| (d) Sinyal darurat jika tekanan turun ≥ 3 hPa dalam 1 jam | `penurunanSatuJam()` mencari selisih terbesar antara tekanan sekarang dan semua sampel dalam 3600 detik terakhir. Pendekatan ini tetap benar walau sampel tidak berjarak sama, karena bangun akibat getaran menambah sampel di luar jadwal. Jika ≥ 3 hPa, buzzer GPIO 25 dan LED GPIO 26 berkedip 10 detik, lalu `alert_reason: "pressure_drop"`. |

**Contoh keluaran JSON:**

```json
{"device_id":"esp32-longsor-node01","cycle":9,"wakeup":"timer","t_s":7201,"sensor_ok":true,
 "temp_c":24.81,"hum_pct":93.2,"pressure_hpa":896.40,"drop_1h_hpa":3.12,
 "vibration_count":2,"history_n":9,"alert":true,"alert_reason":"pressure_drop"}
```

**Catatan rekayasa:**

- Penurunan tekanan udara menandakan cuaca memburuk (badai atau hujan lebat), bukan longsor itu sendiri. Pada sistem nyata seperti SIARENG, sinyal ini sebaiknya digabung dengan kelembapan tanah dan pergeseran kemiringan, bukan dipakai sendirian sebagai alarm longsor.
- Satu-satunya `delay()` ada di fase alarm, dan itu disengaja karena perangkat memang akan langsung tidur setelahnya. Tidak ada tugas lain yang tertahan.
- Konsumsi: aktif ~1 detik per 15 menit (lebih lama saat alarm) dan Deep Sleep di antaranya. Perkiraan arus rata-rata sama dengan C3 Lab-2, yaitu orde 0,1–0,2 mA, cocok untuk baterai dan panel surya kecil.
