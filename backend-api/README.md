# Sistem monitoring SIARENG

Alurnya: ESP32 mencetak JSON ke USB → backend membaca, menyimpan ke SQLite, dan menyiarkan lewat WebSocket → dashboard di browser menampilkan status secara langsung.

```
ESP32 --USB serial------------> backend-api (FastAPI) --WebSocket--> dashboard (browser, laptop/HP)
ESP32 --WiFi, POST /api/telemetry-->   |                 '--> Telegram (opsional)
                                       '--> siareng.db (SQLite, retensi 30 hari)
```

## Menjalankan

Sekali saja, dari folder `backend-api/`:

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
```

**Tanpa alat (mode demo):** buka `dashboard/index.html` langsung di browser, atau jalankan backend lalu buka `http://localhost:8000/?demo`. Gunakan panel "Kendali demo" untuk meniru kondisi lereng.

**Dengan alat lewat USB:** colokkan ESP32, cari nomor port-nya (Windows: Device Manager → Ports, misalnya `COM5`), tutup Serial Monitor PlatformIO (port hanya bisa dipakai satu program), lalu:

```bash
# Windows (Git Bash)
SERIAL_PORT=COM5 .venv/Scripts/python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Buka `http://localhost:8000`. Laptop dan HP di WiFi yang sama bisa membuka `http://<IP-laptop>:8000`.

**Dengan alat lewat WiFi:** set `KIRIM_WIFI 1` di firmware dan isi `firmware/include/secrets.h`. Jalankan perintah yang sama, `SERIAL_PORT` boleh dikosongkan. Langkah lengkap ada di [`docs/panduan-pemula.md`](../docs/panduan-pemula.md).

## Pengaturan (environment variable, semua opsional)

| Nama | Fungsi |
|---|---|
| `SERIAL_PORT`, `SERIAL_BAUD` | Port USB ESP32, misalnya `COM5`. Baud bawaan 115200 |
| `API_KEY` | Bila diisi, `POST /api/telemetry` wajib membawa header `X-API-Key` yang sama |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Kirim pesan Telegram saat status berubah dan saat alat diam lebih dari 60 detik |
| `DB_PATH`, `RETENSI_HARI` | Lokasi SQLite dan lama data disimpan (bawaan 30 hari) |

Jangan menulis token atau kunci ke dalam file yang ikut ter-commit.

## Endpoint

| Metode | Path | Fungsi |
|---|---|---|
| GET | `/` | Dashboard |
| GET | `/api/health` | Cek server hidup dan port serial yang dipakai |
| POST | `/api/telemetry` | Kirim satu pesan firmware (telemetri atau event) dalam format JSON |
| GET | `/api/status` | Pembacaan terakhir dan apakah alat masih mengirim data |
| GET | `/api/history?menit=10` | Riwayat telemetri (maksimal 720 titik, otomatis dijarangkan) dan kejadian |
| GET | `/api/export.csv?menit=1440` | Unduh riwayat sebagai CSV |
| WS | `/ws` | Siaran real-time ke dashboard |
| GET | `/docs` | Dokumentasi OpenAPI otomatis (Swagger) |

Contoh uji tanpa alat:

```bash
curl -X POST localhost:8000/api/telemetry -H "Content-Type: application/json" \
  -d '{"device_id":"esp32-longsor-lereng01","seq":1,"status":"waspada","soil_pct":82,"rain_pct":55,"tilt_delta_deg":0.4,"alert":false}'
```

## Yang belum ada (tahap berikutnya sesuai RPS)

- MQTT (Mosquitto) sebagai jalur utama ESP32 ke server, Minggu 6. Saat ini memakai HTTP POST.
- Basis data time-series (InfluxDB/TimescaleDB) menggantikan SQLite, Minggu 10.
- Docker Compose, TLS, ACL broker, dan JWT, Minggu 11–13. Saat ini pengaman hanya kunci API lewat HTTP biasa, jadi pakai di jaringan lokal saja.
