"""SIARENG backend: penerima telemetri, penyimpanan, WebSocket dashboard, dan peringatan Telegram.

Sumber data (boleh lebih dari satu sekaligus):
  1. Serial USB : set SERIAL_PORT=COM5 (Windows) atau /dev/ttyUSB0 (Linux).
  2. WiFi       : ESP32 mengirim POST /api/telemetry (firmware dengan KIRIM_WIFI = 1).

Pengaturan lewat environment variable (semua opsional):
  SERIAL_PORT, SERIAL_BAUD   port USB ESP32
  API_KEY                    bila diisi, POST /api/telemetry wajib membawa header X-API-Key
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID   kirim peringatan ke Telegram saat status berubah
  DB_PATH, RETENSI_HARI      lokasi SQLite dan lama data disimpan (bawaan 30 hari)

Jalankan:  uvicorn app:app --host 0.0.0.0 --port 8000   lalu buka http://localhost:8000
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import math
import os
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
DASHBOARD = BASE.parent / "dashboard"
DB_PATH = Path(os.getenv("DB_PATH", BASE / "siareng.db"))
SERIAL_PORT = os.getenv("SERIAL_PORT", "")
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "115200"))
API_KEY = os.getenv("API_KEY", "")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
RETENSI_HARI = int(os.getenv("RETENSI_HARI", "30"))
RIWAYAT_AWAL_MENIT = 10        # dikirim ke dashboard saat baru tersambung
DIAM_DETIK = 60                # tanpa data selama ini = perangkat dianggap diam
MAKS_TITIK = 720               # batas titik grafik per permintaan riwayat


def now_ms() -> int:
    return int(time.time() * 1000)


# ----------------------------------------------------------------- penyimpanan
def buka_db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("""CREATE TABLE IF NOT EXISTS telemetry (
        ts INTEGER NOT NULL, device_id TEXT, seq INTEGER, status TEXT,
        soil_pct REAL, rain_pct REAL, tilt_delta_deg REAL, raw TEXT)""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_tel_ts ON telemetry(ts)")
    con.execute("CREATE TABLE IF NOT EXISTS events (ts INTEGER NOT NULL, device_id TEXT, raw TEXT)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_ev_ts ON events(ts)")
    return con


CON = buka_db()
LOCK = threading.Lock()
TERAKHIR: dict[str, Any] = {"ts": 0, "data": None, "sumber": None, "diam_dikabari": False}


def simpan(msg: dict[str, Any], ts: int) -> str:
    """Simpan satu pesan firmware. Mengembalikan jenisnya: telemetry atau event."""
    with LOCK:
        if "event" in msg:
            dev = msg.get("device_id") or (TERAKHIR["data"] or {}).get("device_id")
            CON.execute("INSERT INTO events VALUES (?,?,?)", (ts, dev, json.dumps(msg)))
            CON.commit()
            return "event"
        CON.execute(
            "INSERT INTO telemetry VALUES (?,?,?,?,?,?,?,?)",
            (ts, msg.get("device_id"), msg.get("seq"), msg.get("status"),
             msg.get("soil_pct"), msg.get("rain_pct"), msg.get("tilt_delta_deg"), json.dumps(msg)),
        )
        CON.commit()
        return "telemetry"


def riwayat(menit: int, maks: int = MAKS_TITIK) -> tuple[list, list]:
    batas = now_ms() - menit * 60_000
    with LOCK:
        tel = CON.execute("SELECT ts, raw FROM telemetry WHERE ts >= ? ORDER BY ts", (batas,)).fetchall()
        ev = CON.execute("SELECT ts, raw FROM events WHERE ts >= ? ORDER BY ts DESC LIMIT 100",
                         (min(batas, now_ms() - 24 * 3600_000),)).fetchall()
    if len(tel) > maks:                       # downsampling sederhana: ambil tiap langkah ke-n
        langkah = math.ceil(len(tel) / maks)
        tel = tel[::langkah] + ([tel[-1]] if (len(tel) - 1) % langkah else [])
    return ([{"ts": t, "data": json.loads(r)} for t, r in tel],
            [{"ts": t, "data": json.loads(r)} for t, r in ev])


def bersihkan_lama() -> None:
    batas = int((time.time() - RETENSI_HARI * 86400) * 1000)
    with LOCK:
        CON.execute("DELETE FROM telemetry WHERE ts < ?", (batas,))
        CON.execute("DELETE FROM events WHERE ts < ?", (batas,))
        CON.commit()


# ----------------------------------------------------------------- Telegram
def telegram_aktif() -> bool:
    return bool(TG_TOKEN and TG_CHAT)


def kirim_telegram(teks: str) -> None:
    """Dipanggil di thread terpisah. Kegagalan hanya dicatat, tidak menghentikan server."""
    if not telegram_aktif():
        return
    try:
        data = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": teks}).encode()
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=8) as r:
            r.read()
    except Exception as e:
        print(f"[telegram] gagal mengirim: {e}")


def pesan_status(ke: str, dari: str | None) -> str:
    d = TERAKHIR["data"] or {}
    angka = (f"Tanah {d.get('soil_pct', '?')}% · hujan {d.get('rain_pct', '?')}% · "
             f"kemiringan bergeser {d.get('tilt_delta_deg', '?')}°")
    alat = d.get("device_id", "perangkat")
    if ke == "bahaya":
        return f"🚨 SIARENG: BAHAYA di {alat}\n{angka}\nJauhi area lereng dan periksa kondisi di lokasi."
    if ke == "waspada":
        return f"⚠️ SIARENG: waspada di {alat}\n{angka}"
    return f"✅ SIARENG: {alat} kembali aman (sebelumnya {dari or 'waspada'})\n{angka}"


# ----------------------------------------------------------------- siaran WebSocket
class Hub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    async def kirim_semua(self, payload: dict) -> None:
        for ws in list(self.clients):
            try:
                await ws.send_json(payload)
            except Exception:
                self.clients.discard(ws)

    def terima(self, msg: dict[str, Any], sumber: str) -> None:
        """Dipanggil dari thread mana pun: simpan, siarkan, dan kabari Telegram bila perlu."""
        ts = now_ms()
        jenis = simpan(msg, ts)
        if jenis == "telemetry":
            TERAKHIR.update(ts=ts, data=msg, sumber=sumber)
            if TERAKHIR["diam_dikabari"]:
                TERAKHIR["diam_dikabari"] = False
                threading.Thread(target=kirim_telegram, daemon=True,
                                 args=(f"🔌 SIARENG: {msg.get('device_id', 'perangkat')} kembali mengirim data.",)).start()
        elif msg.get("event") == "status_change" and msg.get("to"):
            threading.Thread(target=kirim_telegram, daemon=True,
                             args=(pesan_status(msg["to"], msg.get("from")),)).start()
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.kirim_semua({"type": jenis, "ts": ts, "data": msg}), self.loop)


HUB = Hub()


# ----------------------------------------------------------------- pembaca serial
def baca_serial(stop: threading.Event) -> None:
    import serial  # pyserial

    while not stop.is_set():
        try:
            with serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1) as port:
                print(f"[serial] terhubung ke {SERIAL_PORT}")
                while not stop.is_set():
                    baris = port.readline().decode("utf-8", errors="ignore").strip()
                    if not baris.startswith("{"):
                        continue          # abaikan log boot ESP32 yang bukan JSON
                    try:
                        msg = json.loads(baris)
                    except json.JSONDecodeError:
                        continue
                    if msg.get("event") in ("wifi", "kirim_gagal"):
                        continue          # catatan diagnostik firmware, bukan data lereng
                    HUB.terima(msg, "serial")
        except Exception as e:  # port dicabut, salah nama port, dsb.
            print(f"[serial] {SERIAL_PORT} belum bisa dibuka ({e}). Coba lagi 3 detik lagi.")
            stop.wait(3)


async def pantau_diam() -> None:
    """Kabari Telegram sekali bila perangkat berhenti mengirim data."""
    while True:
        await asyncio.sleep(10)
        if (telegram_aktif() and TERAKHIR["ts"] and not TERAKHIR["diam_dikabari"]
                and now_ms() - TERAKHIR["ts"] > DIAM_DETIK * 1000):
            TERAKHIR["diam_dikabari"] = True
            alat = (TERAKHIR["data"] or {}).get("device_id", "perangkat")
            teks = (f"🔌 SIARENG: {alat} tidak mengirim data lebih dari {DIAM_DETIK} detik. "
                    "Status lereng tidak diketahui. Periksa daya dan WiFi alat.")
            await asyncio.get_running_loop().run_in_executor(None, kirim_telegram, teks)


@asynccontextmanager
async def lifespan(_: FastAPI):
    HUB.loop = asyncio.get_running_loop()
    bersihkan_lama()
    stop = threading.Event()
    if SERIAL_PORT:
        threading.Thread(target=baca_serial, args=(stop,), daemon=True).start()
    print(f"[siareng] serial={SERIAL_PORT or '-'} | kunci API={'ya' if API_KEY else 'tidak'} | "
          f"Telegram={'ya' if telegram_aktif() else 'tidak'}")
    tugas = asyncio.create_task(pantau_diam())
    yield
    tugas.cancel()
    stop.set()


app = FastAPI(title="SIARENG API", version="0.2.0", lifespan=lifespan,
              description="Telemetri pemantau potensi longsor lereng (ESP32).")


@app.middleware("http")
async def tanpa_cache(request: Request, call_next):
    """Berkas dashboard selalu dicek ulang ke server, supaya pembaruan langsung terlihat."""
    resp = await call_next(request)
    if not request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/api/health", summary="Cek server")
def health() -> dict:
    return {"ok": True, "serial": SERIAL_PORT or None, "kunci_api": bool(API_KEY),
            "telegram": telegram_aktif(), "clients": len(HUB.clients)}


@app.get("/api/status", summary="Pembacaan terakhir dan keadaan perangkat")
def status() -> dict:
    umur = (now_ms() - TERAKHIR["ts"]) / 1000 if TERAKHIR["ts"] else None
    return {"online": umur is not None and umur <= DIAM_DETIK, "umur_detik": umur,
            "sumber": TERAKHIR["sumber"], "ts": TERAKHIR["ts"] or None, "data": TERAKHIR["data"]}


@app.post("/api/telemetry", status_code=202, summary="Terima satu pesan firmware")
async def post_telemetry(req: Request, x_api_key: str | None = Header(default=None)) -> dict:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "Header X-API-Key salah atau belum diisi.")
    try:
        msg = await req.json()
    except Exception:
        raise HTTPException(400, "Body harus JSON, sama dengan baris keluaran firmware.")
    if not isinstance(msg, dict) or not ("event" in msg or {"status", "soil_pct"} <= msg.keys()):
        raise HTTPException(422, "JSON harus berisi field 'event', atau 'status' dan 'soil_pct'.")
    if "status" in msg and msg["status"] not in ("aman", "waspada", "bahaya"):
        raise HTTPException(422, "Field 'status' harus aman, waspada, atau bahaya.")
    HUB.terima(msg, "wifi")
    return {"diterima": True}


@app.get("/api/history", summary="Riwayat telemetri dan kejadian")
def get_history(menit: int = 10) -> dict:
    menit = max(1, min(menit, RETENSI_HARI * 24 * 60))
    tel, ev = riwayat(menit)
    return {"menit": menit, "telemetry": tel, "events": ev}


@app.get("/api/export.csv", summary="Unduh riwayat sebagai CSV")
def export_csv(menit: int = 24 * 60) -> Response:
    batas = now_ms() - max(1, min(menit, RETENSI_HARI * 24 * 60)) * 60_000
    with LOCK:
        baris = CON.execute("SELECT ts, device_id, seq, status, soil_pct, rain_pct, tilt_delta_deg "
                            "FROM telemetry WHERE ts >= ? ORDER BY ts", (batas,)).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["waktu", "device_id", "seq", "status", "soil_pct", "rain_pct", "tilt_delta_deg"])
    for ts, *sisa in baris:
        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts / 1000)), *sisa])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="siareng-riwayat.csv"'})


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    tel, ev = riwayat(RIWAYAT_AWAL_MENIT)
    await ws.send_json({"type": "hello", "history": tel, "events": ev})
    HUB.clients.add(ws)
    try:
        while True:
            await ws.receive_text()   # dashboard tidak mengirim apa-apa; ini menjaga koneksi
    except WebSocketDisconnect:
        pass
    finally:
        HUB.clients.discard(ws)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(DASHBOARD / "index.html")


app.mount("/", StaticFiles(directory=DASHBOARD), name="dashboard")
