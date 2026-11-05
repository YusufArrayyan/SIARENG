"""SIARENG backend: penerima telemetri + WebSocket untuk dashboard.

Sumber data (boleh lebih dari satu sekaligus):
  1. Serial USB  : set SERIAL_PORT=COM5 (Windows) atau /dev/ttyUSB0 (Linux).
                   Membaca baris JSON yang dicetak firmware ke Serial Monitor.
  2. HTTP POST   : POST /api/telemetry dengan body JSON yang sama dengan keluaran firmware.
                   Dipakai nanti saat ESP32 mengirim lewat WiFi (atau dari jembatan MQTT).

Jalankan:
  pip install -r requirements.txt
  SERIAL_PORT=COM5 uvicorn app:app --host 0.0.0.0 --port 8000
Lalu buka http://localhost:8000
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
DASHBOARD = BASE.parent / "dashboard"
DB_PATH = Path(os.getenv("DB_PATH", BASE / "siareng.db"))
SERIAL_PORT = os.getenv("SERIAL_PORT", "")
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "115200"))
RIWAYAT_DETIK = 10 * 60          # yang dikirim ke dashboard saat baru tersambung
RETENSI_HARI = int(os.getenv("RETENSI_HARI", "30"))


# ----------------------------------------------------------------- penyimpanan
def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("""CREATE TABLE IF NOT EXISTS telemetry (
        ts INTEGER NOT NULL, device_id TEXT, seq INTEGER, status TEXT,
        soil_pct REAL, rain_pct REAL, tilt_delta_deg REAL, raw TEXT)""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_tel_ts ON telemetry(ts)")
    con.execute("CREATE TABLE IF NOT EXISTS events (ts INTEGER NOT NULL, device_id TEXT, raw TEXT)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_ev_ts ON events(ts)")
    return con


CON = db()
LOCK = threading.Lock()
LAST_DEVICE = {"id": None}


def simpan(msg: dict[str, Any], ts: int) -> str:
    """Simpan satu pesan firmware. Mengembalikan jenisnya: telemetry atau event."""
    with LOCK:
        if "event" in msg:
            CON.execute("INSERT INTO events VALUES (?,?,?)", (ts, LAST_DEVICE["id"], json.dumps(msg)))
            CON.commit()
            return "event"
        LAST_DEVICE["id"] = msg.get("device_id", LAST_DEVICE["id"])
        CON.execute(
            "INSERT INTO telemetry VALUES (?,?,?,?,?,?,?,?)",
            (ts, msg.get("device_id"), msg.get("seq"), msg.get("status"),
             msg.get("soil_pct"), msg.get("rain_pct"), msg.get("tilt_delta_deg"), json.dumps(msg)),
        )
        CON.commit()
        return "telemetry"


def riwayat(detik: int) -> tuple[list, list]:
    batas = int(time.time() * 1000) - detik * 1000
    with LOCK:
        tel = CON.execute("SELECT ts, raw FROM telemetry WHERE ts >= ? ORDER BY ts", (batas,)).fetchall()
        ev = CON.execute("SELECT ts, raw FROM events ORDER BY ts DESC LIMIT 50").fetchall()
    return ([{"ts": t, "data": json.loads(r)} for t, r in tel],
            [{"ts": t, "data": json.loads(r)} for t, r in ev])


def bersihkan_lama() -> None:
    batas = int((time.time() - RETENSI_HARI * 86400) * 1000)
    with LOCK:
        CON.execute("DELETE FROM telemetry WHERE ts < ?", (batas,))
        CON.execute("DELETE FROM events WHERE ts < ?", (batas,))
        CON.commit()


# ----------------------------------------------------------------- siaran WebSocket
class Hub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    async def kirim_semua(self, payload: dict) -> None:
        mati = []
        for ws in list(self.clients):
            try:
                await ws.send_json(payload)
            except Exception:
                mati.append(ws)
        for ws in mati:
            self.clients.discard(ws)

    def terima(self, msg: dict[str, Any]) -> None:
        """Dipanggil dari thread mana pun: simpan lalu siarkan."""
        ts = int(time.time() * 1000)
        jenis = simpan(msg, ts)
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
                        HUB.terima(json.loads(baris))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:  # port dicabut, salah nama port, dsb.
            print(f"[serial] {SERIAL_PORT} belum bisa dibuka ({e}). Coba lagi 3 detik lagi.")
            stop.wait(3)


@asynccontextmanager
async def lifespan(_: FastAPI):
    HUB.loop = asyncio.get_running_loop()
    bersihkan_lama()
    stop = threading.Event()
    if SERIAL_PORT:
        threading.Thread(target=baca_serial, args=(stop,), daemon=True).start()
    else:
        print("[serial] SERIAL_PORT kosong. Hanya menerima data lewat POST /api/telemetry.")
    yield
    stop.set()


app = FastAPI(title="SIARENG API", version="0.1.0", lifespan=lifespan,
              description="Telemetri pemantau potensi longsor lereng (ESP32).")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "serial": SERIAL_PORT or None, "clients": len(HUB.clients)}


@app.post("/api/telemetry", status_code=202)
async def post_telemetry(req: Request) -> dict:
    try:
        msg = await req.json()
    except Exception:
        raise HTTPException(400, "Body harus JSON, sama dengan baris keluaran firmware.")
    if not isinstance(msg, dict) or not ({"event"} & msg.keys() or {"status", "soil_pct"} <= msg.keys()):
        raise HTTPException(422, "JSON harus berisi field 'event', atau 'status' dan 'soil_pct'.")
    HUB.terima(msg)
    return {"diterima": True}


@app.get("/api/history")
def get_history(menit: int = 10) -> dict:
    tel, ev = riwayat(max(1, min(menit, 24 * 60)) * 60)
    return {"telemetry": tel, "events": ev}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    tel, ev = riwayat(RIWAYAT_DETIK)
    await ws.send_json({"type": "hello", "history": tel, "events": ev})
    HUB.clients.add(ws)
    try:
        while True:
            await ws.receive_text()   # dashboard tidak mengirim apa-apa; ini menjaga koneksi
    except WebSocketDisconnect:
        pass
    finally:
        HUB.clients.discard(ws)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(DASHBOARD / "index.html")


app.mount("/", StaticFiles(directory=DASHBOARD), name="dashboard")
