@echo off
REM ==================================================================
REM  SIARENG - jalankan backend + dashboard dengan sekali klik ganda.
REM  ESP32 lewat USB dicari otomatis (SERIAL_PORT=auto).
REM  Data lewat WiFi diterima di http://<IP-laptop>:8000/api/telemetry
REM ==================================================================
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [1/2] Menyiapkan Python untuk pertama kali, tunggu sebentar...
  python -m venv .venv || (echo Python belum terpasang. Pasang dari python.org lalu ulangi. & pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || (echo Gagal memasang paket. Cek internet. & pause & exit /b 1)
)

if "%SERIAL_PORT%"=="" set SERIAL_PORT=auto

echo.
echo  Dashboard di laptop ini : http://localhost:8000
echo  Dari HP (WiFi yang sama): http://IP-laptop:8000
echo  IP laptop ini:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do echo     %%a
echo  Isi SERVER_URL di firmware\include\secrets.h dengan  http://IP-laptop:8000/api/telemetry
echo  Tutup Serial Monitor PlatformIO agar port USB bisa dibaca. Tekan Ctrl+C untuk berhenti.
echo.

start "" http://localhost:8000
".venv\Scripts\python.exe" -m uvicorn app:app --host 0.0.0.0 --port 8000
pause
