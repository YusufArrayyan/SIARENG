"""Membuat docs/Panduan_SIARENG.pdf dari HTML bergambar.

Jalankan dari folder proyek:
    python docs/panduan-pdf/buat_pdf.py
Butuh Microsoft Edge atau Google Chrome (dipakai untuk mencetak HTML ke PDF).
"""
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HTML = HERE / "panduan.html"
PDF = HERE.parent / "Panduan_SIARENG.pdf"

BLUE, INK, INK2, RED, YEL, GRN = "#0066cc", "#1d1d1f", "#6e6e73", "#e0302a", "#e6a100", "#2a9d4b"
WIRE = {"3V3": "#e0302a", "GND": "#1d1d1f", "SDA": "#2f7de1", "SCL": "#e6a100", "SIG": "#8a4fd8", "ADC": "#16a085"}


# ------------------------------------------------------------------ gambar SVG
def esp32_kabel(judul, pins, komponen, catatan=""):
    """Diagram sambungan: papan ESP32 di kiri, satu komponen di kanan, kabel berwarna di antaranya.
    pins = [(label pin ESP32, label pin komponen, warna)]"""
    n = len(pins)
    row = 34
    h = max(170, 60 + n * row)
    y0 = (h - (n - 1) * row) / 2
    s = [f'<svg viewBox="0 0 640 {h}" class="dg" role="img" aria-label="{judul}">']
    # papan ESP32
    s.append(f'<rect x="20" y="16" width="170" height="{h-32}" rx="12" fill="#22262b"/>')
    s.append(f'<rect x="55" y="{h/2-38}" width="80" height="62" rx="4" fill="#b8bcc2"/>')
    s.append(f'<text x="95" y="{h/2-2}" class="chip-t" text-anchor="middle">ESP32</text>')
    s.append(f'<rect x="80" y="{h-30}" width="30" height="14" rx="2" fill="#8d9096"/>')
    # komponen
    s.append(f'<rect x="440" y="{y0-26}" width="180" height="{(n-1)*row+52}" rx="12" fill="#f5f5f7" stroke="#d2d2d7"/>')
    s.append(f'<text x="530" y="{y0-34}" class="lbl" text-anchor="middle">{komponen}</text>')
    for i, (pe, pk, w) in enumerate(pins):
        y = y0 + i * row
        col = WIRE.get(w, w)
        s.append(f'<circle cx="190" cy="{y}" r="5" fill="#d9b44a" stroke="#22262b" stroke-width="2"/>')
        s.append(f'<text x="178" y="{y+4}" class="pin-e" text-anchor="end">{pe}</text>')
        s.append(f'<path d="M195 {y} C 300 {y}, 330 {y}, 435 {y}" stroke="{col}" stroke-width="4" fill="none" stroke-linecap="round"/>')
        s.append(f'<circle cx="440" cy="{y}" r="5" fill="#fff" stroke="{col}" stroke-width="2.5"/>')
        s.append(f'<text x="454" y="{y+4}" class="pin-k">{pk}</text>')
    s.append("</svg>")
    if catatan:
        s.append(f'<p class="cap">{catatan}</p>')
    return "\n".join(s)


def peta_lengkap():
    """Semua sambungan dalam satu gambar."""
    rows = [
        ("3V3", "VCC semua sensor", "3V3", "Jalur merah breadboard"),
        ("GND", "GND semua komponen", "GND", "Jalur biru breadboard"),
        ("GPIO 21", "SDA", "SDA", "MPU6050"),
        ("GPIO 22", "SCL", "SCL", "MPU6050"),
        ("GPIO 34", "AOUT", "ADC", "Sensor tanah"),
        ("GPIO 35", "AO", "ADC", "Modul sensor hujan"),
        ("GPIO 26", "lewat resistor", "#2a9d4b", "LED hijau"),
        ("GPIO 27", "lewat resistor", "#e6a100", "LED kuning"),
        ("GPIO 14", "lewat resistor", "#e0302a", "LED merah"),
        ("GPIO 25", "S (sinyal)", "SIG", "Buzzer"),
        ("GPIO 15", "Kaki tombol", "#5f6b7a", "Tombol (kaki lain ke GND)"),
    ]
    row = 38
    h = 40 + len(rows) * row
    s = [f'<svg viewBox="0 0 640 {h}" class="dg" role="img" aria-label="Peta sambungan lengkap">']
    s.append(f'<rect x="20" y="10" width="150" height="{h-20}" rx="12" fill="#22262b"/>')
    s.append(f'<text x="95" y="{h/2+5}" class="chip-t" text-anchor="middle" transform="rotate(-90 95 {h/2})">ESP32 DevKit</text>')
    for i, (pe, pk, w, komp) in enumerate(rows):
        y = 30 + i * row
        col = WIRE.get(w, w)
        s.append(f'<circle cx="170" cy="{y}" r="5" fill="#d9b44a" stroke="#22262b" stroke-width="2"/>')
        s.append(f'<text x="158" y="{y+4}" class="pin-e" text-anchor="end">{pe}</text>')
        s.append(f'<line x1="175" y1="{y}" x2="330" y2="{y}" stroke="{col}" stroke-width="4" stroke-linecap="round"/>')
        s.append(f'<rect x="335" y="{y-14}" width="285" height="28" rx="8" fill="#f5f5f7" stroke="#d2d2d7"/>')
        s.append(f'<text x="347" y="{y+4}" class="pin-k"><tspan font-weight="600">{komp}</tspan> · {pk}</text>')
    s.append("</svg>")
    return "\n".join(s)


def alur():
    box = lambda x, y, w, t, sub, fill="#f5f5f7": (
        f'<rect x="{x}" y="{y}" width="{w}" height="64" rx="12" fill="{fill}" stroke="#d2d2d7"/>'
        f'<text x="{x+w/2}" y="{y+28}" class="lbl" text-anchor="middle">{t}</text>'
        f'<text x="{x+w/2}" y="{y+48}" class="sub" text-anchor="middle">{sub}</text>')
    arr = lambda x1, y1, x2, y2, t="": (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{BLUE}" stroke-width="2.5" marker-end="url(#ah)"/>'
        + (f'<text x="{(x1+x2)/2}" y="{min(y1,y2)-8}" class="sub" text-anchor="middle">{t}</text>' if t else ""))
    s = ['<svg viewBox="0 0 640 250" class="dg" role="img" aria-label="Alur data SIARENG">',
         f'<defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M1 1L9 5L1 9z" fill="{BLUE}"/></marker></defs>',
         box(10, 20, 140, "3 sensor", "tanah, hujan, miring"),
         box(10, 160, 140, "LED + buzzer", "alarm di lokasi", "#fff4e5"),
         box(220, 90, 130, "ESP32", "putuskan status", "#e6f1fb"),
         box(420, 90, 200, "Backend (laptop)", "terima dan simpan"),
         box(420, 186, 95, "Dashboard", "laptop / HP"),
         box(525, 186, 95, "Telegram", "opsional"),
         arr(150, 52, 218, 108), arr(218, 140, 152, 186),
         arr(350, 122, 418, 122, "USB / WiFi"),
         arr(470, 154, 468, 184), arr(570, 154, 572, 184),
         "</svg>"]
    return "\n".join(s)


def lereng(status="aman"):
    led = {"aman": GRN, "waspada": YEL, "bahaya": RED}[status]
    tilt = {"aman": 0, "waspada": 8, "bahaya": 18}[status]
    return f'''<svg viewBox="0 0 300 200" class="scene">
<g stroke="#378add" stroke-width="2" stroke-linecap="round" opacity="{0 if status=='aman' else .8}">
<path d="M40 18l-6 16M78 8l-6 16M116 22l-6 16M154 6l-6 16M192 20l-6 16M230 10l-6 16M268 24l-6 16M60 52l-6 16M134 50l-6 16M212 54l-6 16"/></g>
<path d="M0 172 L300 84 L300 200 L0 200 Z" fill="{'#dccfb4' if status=='aman' else '#9a7a4e'}"/>
<path d="M0 172 L300 84" stroke="#1d1d1f" stroke-width="2" opacity=".55"/>
<line x1="170" y1="122" x2="170" y2="52" stroke="#1d1d1f" stroke-width="1.5" stroke-dasharray="4 5" opacity=".35"/>
<g transform="rotate({tilt} 170 122)">
<line x1="170" y1="140" x2="170" y2="60" stroke="#1d1d1f" stroke-width="4" stroke-linecap="round"/>
<rect x="155" y="62" width="30" height="24" rx="4" fill="#fff" stroke="#1d1d1f" stroke-width="2"/>
<circle cx="170" cy="74" r="4.5" fill="{led}"/>
<path d="M150 54 L190 46" stroke="#1d1d1f" stroke-width="4" stroke-linecap="round"/></g>
<path d="M185 82 C206 86 214 96 214 112 L214 126" fill="none" stroke="#1d1d1f" stroke-width="1.5" opacity=".7"/></svg>'''


def breadboard():
    s = ['<svg viewBox="0 0 640 220" class="dg" role="img" aria-label="Cara kerja breadboard">',
         '<rect x="20" y="10" width="600" height="200" rx="10" fill="#f1efe8" stroke="#c9c6bb"/>']
    for yy, c in ((26, RED), (40, "#2f7de1"), (180, RED), (194, "#2f7de1")):
        s.append(f'<line x1="40" y1="{yy}" x2="600" y2="{yy}" stroke="{c}" stroke-width="1.5"/>')
    s.append('<rect x="30" y="106" width="580" height="8" fill="#ddd9cc"/>')
    for col in range(28):
        x = 50 + col * 20
        for r in range(5):
            s.append(f'<rect x="{x-3}" y="{56+r*10-3}" width="6" height="6" rx="1" fill="#55524a"/>')
            s.append(f'<rect x="{x-3}" y="{122+r*10-3}" width="6" height="6" rx="1" fill="#55524a"/>')
    # sorot satu kolom dan satu jalur
    s.append(f'<rect x="183" y="48" width="14" height="52" rx="4" fill="none" stroke="{BLUE}" stroke-width="2.5"/>')
    s.append(f'<rect x="36" y="20" width="568" height="12" rx="4" fill="none" stroke="{BLUE}" stroke-width="2.5"/>')
    s.append('</svg>')
    s.append('<p class="cap">Kotak biru: 5 lubang dalam satu kolom pendek saling tersambung. Jalur panjang di tepi '
             '(merah = +, biru = −) tersambung sepanjang papan. Celah di tengah memisahkan bagian atas dan bawah.</p>')
    return "\n".join(s)


def jaringan():
    return f'''<svg viewBox="0 0 640 170" class="dg" role="img" aria-label="ESP32 dan laptop di WiFi yang sama">
<defs><marker id="ah2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M1 1L9 5L1 9z" fill="{BLUE}"/></marker></defs>
<rect x="20" y="50" width="150" height="70" rx="12" fill="#e6f1fb" stroke="#b5d4f4"/>
<text x="95" y="80" class="lbl" text-anchor="middle">ESP32</text><text x="95" y="100" class="sub" text-anchor="middle">di lereng</text>
<rect x="245" y="50" width="150" height="70" rx="12" fill="#f5f5f7" stroke="#d2d2d7"/>
<text x="320" y="80" class="lbl" text-anchor="middle">Router / hotspot</text><text x="320" y="100" class="sub" text-anchor="middle">WiFi 2,4 GHz</text>
<rect x="470" y="50" width="150" height="70" rx="12" fill="#f5f5f7" stroke="#d2d2d7"/>
<text x="545" y="80" class="lbl" text-anchor="middle">Laptop</text><text x="545" y="100" class="sub" text-anchor="middle">192.168.1.10:8000</text>
<line x1="172" y1="85" x2="240" y2="85" stroke="{BLUE}" stroke-width="2.5" stroke-dasharray="6 5" marker-end="url(#ah2)"/>
<line x1="397" y1="85" x2="465" y2="85" stroke="{BLUE}" stroke-width="2.5" stroke-dasharray="6 5" marker-end="url(#ah2)"/>
<text x="320" y="150" class="sub" text-anchor="middle">ESP32 mengirim ke alamat IP laptop. Keduanya harus tersambung ke WiFi yang sama.</text>
</svg>'''


# ------------------------------------------------------------------ isi
def langkah(no, judul, waktu, isi, berhasil):
    return f'''<section class="step">
<div class="step-head"><span class="num">{no}</span><div><h2>{judul}</h2><p class="meta">{waktu}</p></div></div>
{isi}
<div class="ok"><b>Berhasil kalau</b> {berhasil}</div>
</section>'''


def sub(no, judul, isi, berhasil):
    return f'''<section class="substep"><h3><span class="snum">{no}</span>{judul}</h3>{isi}
<div class="ok"><b>Berhasil kalau</b> {berhasil}</div></section>'''


def code(t):
    return f'<pre>{t}</pre>'


today = datetime.date.today().strftime("%d-%m-%Y")

body = f'''
<section class="cover">
  <p class="eyebrow">Teknologi IoT · Informatika UNIB</p>
  <h1>Panduan membuat<br>SIARENG</h1>
  <p class="lead">Alat pemantau potensi longsor lereng berbasis ESP32.<br>Dari nol sampai data tampil di dashboard.</p>
  <div class="cover-art">
    <figure>{lereng("aman")}<figcaption><span class="dot g"></span>Aman</figcaption></figure>
    <figure>{lereng("waspada")}<figcaption><span class="dot y"></span>Waspada</figcaption></figure>
    <figure>{lereng("bahaya")}<figcaption><span class="dot r"></span>Bahaya</figcaption></figure>
  </div>
  <p class="cover-foot">Versi {today} · github.com/YusufArrayyan/SIARENG</p>
</section>

<section class="page">
  <h2 class="big">Isi panduan</h2>
  <table class="toc">
    <tr><th>Langkah</th><th>Yang dikerjakan</th><th>Butuh alat?</th><th>Waktu</th></tr>
    <tr><td>1</td><td>Siapkan laptop</td><td>Tidak</td><td>1 jam</td></tr>
    <tr><td>2</td><td>Ambil kode SIARENG</td><td>Tidak</td><td>5 menit</td></tr>
    <tr><td>3</td><td>Coba simulasi dan dashboard demo</td><td>Tidak</td><td>30 menit</td></tr>
    <tr><td>4</td><td>Beli komponen</td><td></td><td>menunggu kiriman</td></tr>
    <tr><td>5</td><td>Rakit di breadboard, satu komponen per tahap</td><td>Ya</td><td>2–3 jam</td></tr>
    <tr><td>6</td><td>Kalibrasi sensor</td><td>Ya</td><td>30 menit</td></tr>
    <tr><td>7</td><td>Sambungkan ke dashboard lewat kabel USB</td><td>Ya</td><td>15 menit</td></tr>
    <tr><td>8</td><td>Kirim data lewat WiFi</td><td>Ya</td><td>30 menit</td></tr>
    <tr><td>9</td><td>Peringatan ke Telegram (opsional)</td><td>Ya</td><td>20 menit</td></tr>
    <tr><td>10</td><td>Pasang di lapangan</td><td>Ya</td><td>lihat panduan perakitan</td></tr>
  </table>
  <div class="note"><b>Cara memakai panduan ini.</b> Kerjakan berurutan. Setiap langkah ditutup kotak hijau
  <b>"Berhasil kalau"</b>. Jangan lanjut sebelum tanda itu terlihat, supaya kalau ada masalah kamu tahu persis di langkah mana penyebabnya.
  Langkah 1 sampai 3 tidak butuh alat, jadi bisa dikerjakan sambil menunggu kiriman komponen.</div>
  <div class="warn">SIARENG adalah alat pembelajaran. Ambang statusnya masih nilai awal untuk uji, bukan hasil kajian geologi,
  dan alat ini bukan sistem peringatan dini resmi. Untuk keadaan darurat, ikuti arahan BPBD setempat.</div>
</section>

<section class="page">
  <h2 class="big">Cara kerja SIARENG</h2>
  {alur()}
  <ol class="flow">
    <li><b>Tiga sensor</b> mengukur kelembapan tanah, hujan, dan pergeseran kemiringan.</li>
    <li><b>ESP32</b> membaca sensor 5 kali per detik, lalu memutuskan status: aman, waspada, atau bahaya.</li>
    <li><b>LED dan buzzer</b> memberi peringatan langsung di lokasi. Bagian ini tetap bekerja walaupun internet mati.</li>
    <li>ESP32 juga mengirim datanya ke <b>backend</b> di laptop, yang menyimpan data dan meneruskannya ke <b>dashboard</b> serta Telegram.</li>
  </ol>
  <h3>Aturan status</h3>
  <table>
    <tr><th>Status</th><th>Syarat</th><th>Yang terjadi di alat</th></tr>
    <tr><td><span class="dot g"></span>Aman</td><td>Selain kondisi di bawah</td><td>LED hijau</td></tr>
    <tr><td><span class="dot y"></span>Waspada</td><td>Tanah jenuh (≥ 80%), atau lereng bergeser ≥ 2°, atau tanah basah (≥ 60%) saat hujan deras (≥ 40%)</td><td>LED kuning, bip tiap 3 detik</td></tr>
    <tr><td><span class="dot r"></span>Bahaya</td><td>Tanah jenuh (≥ 80%) <b>dan</b> lereng bergeser ≥ 5°</td><td>LED merah berkedip, buzzer terus berbunyi</td></tr>
  </table>
  <p class="small">Status naik hanya kalau kondisinya bertahan 2 detik, dan turun kalau sudah bertahan 6 detik. Jeda ini mencegah alarm palsu saat sensor tersenggol sebentar.</p>
</section>

<section class="page">
  <h2 class="big">Kenali komponennya</h2>
  <div class="grid">
    <div class="card"><h4>ESP32</h4><p>Membaca sensor, memutuskan status, mengirim data.</p><p class="ana">Otak alat</p></div>
    <div class="card"><h4>MPU6050 (GY-521)</h4><p>Mengukur kemiringan terhadap gravitasi.</p><p class="ana">Waterpas digital</p></div>
    <div class="card"><h4>Sensor tanah kapasitif</h4><p>Mengukur seberapa basah tanah.</p><p class="ana">Jari yang ditancap ke tanah</p></div>
    <div class="card"><h4>Sensor hujan</h4><p>Mendeteksi air di permukaan panel.</p><p class="ana">Telapak tangan yang menadah hujan</p></div>
    <div class="card"><h4>LED hijau, kuning, merah</h4><p>Menunjukkan status di lokasi.</p><p class="ana">Lampu lalu lintas</p></div>
    <div class="card"><h4>Buzzer</h4><p>Bunyi peringatan.</p><p class="ana">Peluit</p></div>
    <div class="card"><h4>Tombol</h4><p>Menetapkan posisi sekarang sebagai "normal".</p><p class="ana">Tombol nol pada timbangan</p></div>
    <div class="card"><h4>Breadboard dan jumper</h4><p>Menyambung komponen tanpa solder.</p><p class="ana">Papan colok</p></div>
  </div>
  <h3>Peta sambungan lengkap</h3>
  <p class="small">Simpan halaman ini. Semua sambungan di Langkah 5 merujuk ke peta ini.</p>
  {peta_lengkap()}
</section>

{langkah(1, "Siapkan laptop", "Tidak butuh alat · sekitar 1 jam", f"""
<p>Pasang empat program ini. Semuanya gratis.</p>
<ol>
<li><b>Visual Studio Code</b>: code.visualstudio.com</li>
<li><b>Git</b>: git-scm.com. Di Windows, biarkan semua pilihan bawaan saat memasang.</li>
<li><b>Python 3.10 atau lebih baru</b>: python.org/downloads. Di Windows, centang <b>"Add python.exe to PATH"</b> di layar pertama.</li>
<li>Di VS Code, buka Extensions (<code>Ctrl+Shift+X</code>), lalu pasang:
<ul><li><b>PlatformIO IDE</b>. Tunggu tulisan "Installing PlatformIO Core" di pojok bawah hilang (5–10 menit).</li>
<li><b>Wokwi Simulator</b>. Tekan <code>F1</code>, ketik <code>Wokwi: Request a New License</code>, ikuti halaman yang terbuka.</li></ul></li>
</ol>
<p>Cek di terminal:</p>{code("git --version\npython --version")}""",
"ikon kepala semut (PlatformIO) muncul di bilah kiri VS Code, dan kedua perintah di atas menampilkan nomor versi.")}

{langkah(2, "Ambil kode SIARENG", "Tidak butuh alat · 5 menit", f"""
<p>Buka terminal di VS Code (menu Terminal → New Terminal), pindah ke folder tempat menyimpan proyek, lalu jalankan:</p>
{code("git clone https://github.com/YusufArrayyan/SIARENG.git")}
<table><tr><th>Folder</th><th>Isi</th></tr>
<tr><td><code>firmware/</code></td><td>Program yang ditanam ke ESP32</td></tr>
<tr><td><code>dashboard/</code></td><td>Halaman web pemantau</td></tr>
<tr><td><code>backend-api/</code></td><td>Program Python penghubung ESP32 dan dashboard</td></tr>
<tr><td><code>docs/</code></td><td>Panduan, RAB, laporan</td></tr></table>""",
"folder <code>SIARENG</code> muncul dan berisi folder-folder di atas.")}

{langkah(3, "Coba tanpa alat", "Tidak butuh alat · 30 menit", """
<h3>3a. Simulasi alat di Wokwi</h3>
<ol><li>Di VS Code, File → Open Folder, buka <b><code>SIARENG/firmware</code></b> (bukan folder <code>SIARENG</code>).</li>
<li>Klik ikon PlatformIO → <b>Build</b>. Build pertama lama karena mengunduh perkakas ESP32.</li>
<li>Tekan <code>F1</code> → <code>Wokwi: Start Simulator</code>.</li>
<li>Putar potensiometer (tanah dan hujan) dan geser slider MPU6050. Skenario lengkap ada di <code>docs/simulasi-demo.md</code>.</li></ol>
<h3>3b. Dashboard mode demo</h3>
<p>Klik dua kali file <code>SIARENG/dashboard/index.html</code>. Di bagian "Kendali demo", tekan <b>Lereng bergerak</b>.
Setelah 2 detik panel besar berubah menjadi <b>Bahaya</b> dan muncul banner merah.</p>""",
"LED hijau menyala di simulasi Wokwi, dan saat tanah dibuat jenuh sambil kemiringan digeser, LED merah berkedip.")}

{langkah(4, "Beli komponen", "Menunggu kiriman", """
<p>Pakai daftar di <code>docs/RAB_SIARENG_hemat.xlsx</code>, sekitar <b>Rp210.000</b> termasuk ongkir. Setiap baris sudah berisi link toko dan varian yang harus dipilih saat checkout.</p>
<table><tr><th>Komponen</th><th>Jumlah</th></tr>
<tr><td>ESP32 DevKit + kabel data micro USB</td><td>1</td></tr>
<tr><td>MPU6050 (GY-521)</td><td>1</td></tr>
<tr><td>Sensor kelembapan tanah kapasitif v1.2</td><td>1</td></tr>
<tr><td>Modul sensor hujan (raindrop)</td><td>1</td></tr>
<tr><td>Buzzer pasif</td><td>1</td></tr>
<tr><td>LED 5 mm merah, kuning, hijau + resistor 220–330 Ω</td><td>3 + 3</td></tr>
<tr><td>Push button</td><td>1</td></tr>
<tr><td>Breadboard 830 titik, jumper male-male dan male-female</td><td>1 + 2 set</td></tr></table>
<p class="small">Solder belum diperlukan untuk tahap uji. Kalau kabel USB yang kamu punya hanya untuk mengisi daya (tidak bisa transfer data), ESP32 tidak akan terdeteksi.</p>""",
"semua barang di tabel sudah ada di mejamu.")}

<section class="step">
<div class="step-head"><span class="num">5</span><div><h2>Rakit di breadboard</h2><p class="meta">Butuh alat · 2–3 jam</p></div></div>
<p><b>Kuncinya: pasang satu komponen, uji, baru pasang berikutnya.</b> Kalau semua dipasang sekaligus lalu ada yang salah, sulit mencari penyebabnya.</p>
<h3>Yang perlu dipahami dulu</h3>
{breadboard()}
<ul>
<li><b>Label pin ESP32</b> bisa tertulis <code>D21</code>, <code>G21</code>, <code>IO21</code>, atau <code>21</code>. Semuanya berarti GPIO 21.</li>
<li><b>Cabut kabel USB setiap kali mengubah sambungan.</b></li>
<li><b>Semua sensor diberi daya dari pin <code>3V3</code></b>, jangan dari <code>VIN</code> atau <code>5V</code>.</li>
<li>Warna kabel di gambar hanya penanda. Kamu boleh memakai warna apa saja, asalkan sambungannya sama.</li>
</ul>
</section>

{sub("5.1", "ESP32 saja", esp32_kabel("ESP32 ke breadboard", [("3V3", "Jalur merah (+)", "3V3"), ("GND", "Jalur biru (−)", "GND")], "Breadboard") + """
<ol><li>Tancapkan ESP32 melintang di atas celah tengah. Kalau papanmu versi lebar (38 pin) dan satu sisi tidak menyisakan lubang,
pin di sisi itu disambung dengan jumper <b>male-female</b> langsung ke kaki ESP32.</li>
<li>Buka <code>firmware/include/config.h</code>, ubah <code>#define SIMULASI 1</code> menjadi <code>0</code>.</li>
<li>Colokkan USB. Di VS Code (folder <code>firmware</code> terbuka): PlatformIO → <b>Upload</b>. Kalau berhenti di <code>Connecting.....</code>, tahan tombol <b>BOOT</b> di ESP32.</li>
<li>PlatformIO → <b>Monitor</b>.</li></ol>
<p class="small">Port tidak terdeteksi? Lihat chip kecil di dekat port USB ESP32: <b>CP2102</b> (pasang driver "CP210x" dari Silicon Labs) atau <b>CH340</b> (pasang driver "CH340").</p>""",
"Monitor menampilkan <code>{\"event\":\"boot\"}</code> lalu <code>MPU6050 tidak terdeteksi</code>. Pesan error ini wajar karena sensornya belum dipasang.")}

{sub("5.2", "MPU6050 (kemiringan)", esp32_kabel("MPU6050", [("3V3", "VCC", "3V3"), ("GND", "GND", "GND"), ("GPIO 21", "SDA", "SDA"), ("GPIO 22", "SCL", "SCL")], "MPU6050 (GY-521)") + """
<p>Colok USB lagi, lalu tekan tombol <b>EN</b> (atau RST) di ESP32 untuk memulai ulang.</p>""",
"pesan error hilang, muncul <code>baseline_siap</code>, lalu baris data tiap 2 detik. Saat breadboard dimiringkan, nilai <code>tilt_delta_deg</code> naik.")}

{sub("5.3", "Tiga LED", esp32_kabel("LED", [("GPIO 26", "Resistor → kaki panjang LED hijau", "#2a9d4b"), ("GPIO 27", "Resistor → kaki panjang LED kuning", "#e6a100"), ("GPIO 14", "Resistor → kaki panjang LED merah", "#e0302a"), ("GND", "Kaki pendek ketiga LED", "GND")], "3 LED + 3 resistor") + """
<p>Kaki <b>panjang</b> LED (anoda) disambung ke resistor, ujung resistor lain ke GPIO. Kaki <b>pendek</b> (katoda) ke jalur biru.
LED yang terbalik tidak rusak, hanya tidak menyala.</p>""",
"setelah restart, LED kuning menyala 2 detik (alat mengambil patokan kemiringan), lalu berganti hijau. Miringkan breadboard lebih dari 2°: setelah 2 detik LED kuning menyala.")}

{sub("5.4", "Buzzer", esp32_kabel("Buzzer", [("GPIO 25", "S atau I/O (sinyal)", "SIG"), ("GND", "− atau GND", "GND"), ("3V3", "+ atau VCC (kalau ada)", "3V3")], "Buzzer pasif"),
"saat status waspada (breadboard dimiringkan), terdengar bip pendek tiap 3 detik.")}

{sub("5.5", "Tombol kalibrasi", esp32_kabel("Tombol", [("GPIO 15", "Kaki 1", "#5f6b7a"), ("GND", "Kaki diagonal", "GND")], "Push button") + """
<p>Tancapkan tombol melintang di celah tengah breadboard. Pakai dua kaki yang berseberangan secara diagonal.</p>""",
"saat ditekan, Monitor menampilkan <code>kalibrasi_ulang</code>, dan posisi miring saat itu dianggap normal (LED kembali hijau).")}

{sub("5.6", "Sensor tanah", esp32_kabel("Sensor tanah", [("3V3", "VCC", "3V3"), ("GND", "GND", "GND"), ("GPIO 34", "AOUT", "ADC")], "Sensor tanah kapasitif") + """
<p>Bagian yang boleh basah hanya sampai garis putih di badan sensor. Komponen elektronik di bagian atas harus tetap kering.</p>""",
"nilai <code>soil_raw</code> berubah saat bagian bawah sensor digenggam atau dicelup ke air.")}

{sub("5.7", "Sensor hujan", esp32_kabel("Sensor hujan", [("3V3", "VCC", "3V3"), ("GND", "GND", "GND"), ("GPIO 35", "AO (bukan DO)", "ADC")], "Modul komparator hujan") + """
<p>Sensor hujan terdiri dari panel bergaris dan modul kecil. Sambungkan panel ke modul dengan dua kabel pendek bawaannya. Pin <b>DO</b> tidak dipakai.</p>""",
"nilai <code>rain_raw</code> turun saat panel ditetesi air. Rangkaianmu sekarang lengkap.")}

{langkah(6, "Kalibrasi sensor", "Butuh alat · 30 menit", f"""
<p>Setiap sensor sedikit berbeda, jadi alat perlu tahu angka "kering" dan "basah" milik sensormu. Lihat nilai <code>soil_raw</code> dan <code>rain_raw</code> di Monitor.</p>
<table><tr><th>Yang diukur</th><th>Caranya</th><th>Isi ke <code>config.h</code></th></tr>
<tr><td>Tanah kering</td><td>Sensor dibiarkan di udara</td><td><code>SOIL_RAW_KERING</code></td></tr>
<tr><td>Tanah basah</td><td>Sensor dicelup air sampai garis batas</td><td><code>SOIL_RAW_BASAH</code></td></tr>
<tr><td>Hujan kering</td><td>Panel dilap sampai kering</td><td><code>RAIN_RAW_KERING</code></td></tr>
<tr><td>Hujan basah</td><td>Seluruh panel dibasahi</td><td><code>RAIN_RAW_BASAH</code></td></tr></table>
<p>Isi keempat angka di blok <code>#else</code> ("NILAI CONTOH untuk sensor asli") di <code>firmware/include/config.h</code>:</p>
{code("constexpr int SOIL_RAW_KERING = 3200;   // ganti dengan hasil ukurmu\nconstexpr int SOIL_RAW_BASAH  = 1400;\nconstexpr int RAIN_RAW_KERING = 4095;\nconstexpr int RAIN_RAW_BASAH  = 1200;")}
<p>Upload lagi, lalu uji skenario bahaya: celup sensor tanah, miringkan breadboard lebih dari 5°, tunggu 2 detik.</p>""",
"<code>soil_pct</code> mendekati 0 di udara dan mendekati 100 di air, dan pada skenario bahaya LED merah berkedip serta buzzer berbunyi.")}

{langkah(7, "Sambungkan ke dashboard lewat USB", "Butuh alat · 15 menit", f"""
<p>Siapkan backend, cukup sekali. Buka terminal di folder <code>SIARENG/backend-api</code>:</p>
{code("python -m venv .venv\n.venv/Scripts/pip install -r requirements.txt")}
<p>Cari nomor port ESP32 di Device Manager → Ports (COM &amp; LPT), misalnya <code>COM5</code>.
<b>Tutup Monitor PlatformIO</b> karena satu port hanya bisa dipakai satu program. Lalu jalankan backend:</p>
<p class="small">Git Bash:</p>{code("SERIAL_PORT=COM5 .venv/Scripts/python -m uvicorn app:app --host 0.0.0.0 --port 8000")}
<p class="small">PowerShell:</p>{code('$env:SERIAL_PORT="COM5"; .venv\\Scripts\\python -m uvicorn app:app --host 0.0.0.0 --port 8000')}
<p>Buka <b>http://localhost:8000</b> di browser.</p>""",
"pojok kanan atas dashboard bertuliskan \"Menerima data dari alat\", dan angka di layar ikut berubah saat sensor dibasahi atau breadboard dimiringkan.")}

{langkah(8, "Kirim data lewat WiFi", "Butuh alat · 30 menit", f"""
<p>Dengan WiFi, alat tidak perlu menempel ke laptop. Cukup beri daya dari adaptor atau powerbank.</p>
{jaringan()}
<ol>
<li>Cari IP laptop: jalankan <code>ipconfig</code>, catat angka di baris <b>IPv4 Address</b>, misalnya <code>192.168.1.10</code>.</li>
<li>Di <code>firmware/include/</code>, salin <code>secrets.example.h</code> menjadi <code>secrets.h</code>, lalu isi:
{code('#define WIFI_SSID  "nama WiFi kamu"\n#define WIFI_PASS  "kata sandi WiFi"\n#define SERVER_URL "http://192.168.1.10:8000/api/telemetry"\n#define API_KEY    ""')}
<span class="small">File <code>secrets.h</code> tidak ikut ter-commit ke GitHub, jadi kata sandi WiFi tidak tersebar.</span></li>
<li>Di <code>config.h</code>, ubah <code>#define KIRIM_WIFI 0</code> menjadi <code>1</code>, lalu Upload.</li>
<li>Jalankan backend seperti Langkah 7. Bagian <code>SERIAL_PORT=COM5</code> boleh dihapus.</li>
<li>Saat Windows bertanya soal firewall, pilih <b>Allow access</b>.</li>
</ol>
<div class="note"><b>Syarat WiFi:</b> ESP32 dan laptop di jaringan yang sama, dan jaringannya <b>2,4 GHz</b> (ESP32 tidak bisa 5 GHz). Hotspot HP bisa dipakai.
Dashboard juga bisa dibuka dari HP di WiFi yang sama: <code>http://192.168.1.10:8000</code>.</div>
<p class="small"><b>Kunci API (disarankan).</b> Isi kata kunci yang sama di <code>secrets.h</code> (<code>API_KEY</code>) dan saat menjalankan backend (<code>API_KEY=kunci-kamu</code> di depan perintah), supaya server hanya menerima data dari alatmu.</p>""",
"Monitor menampilkan <code>{\"event\":\"wifi\",\"ip\":...}</code>, dan dashboard tetap menerima data setelah kabel USB dicabut dan ESP32 diberi daya dari adaptor atau powerbank.")}

{langkah(9, "Peringatan ke Telegram (opsional)", "Butuh alat · 20 menit", f"""
<ol>
<li>Di Telegram, buka <b>@BotFather</b>, kirim <code>/newbot</code>, ikuti petunjuknya, dan simpan <b>token</b> yang diberikan. Perlakukan token seperti kata sandi.</li>
<li>Kirim pesan apa saja ke bot barumu.</li>
<li>Buka <code>https://api.telegram.org/botTOKEN/getUpdates</code> di browser (ganti TOKEN), lalu cari angka setelah <code>"chat":{{"id":</code>. Itu <b>chat ID</b>.</li>
<li>Jalankan backend dengan dua pengaturan tambahan:
{code("TELEGRAM_BOT_TOKEN=token-kamu TELEGRAM_CHAT_ID=123456789 \\\n  .venv/Scripts/python -m uvicorn app:app --host 0.0.0.0 --port 8000")}</li>
</ol>
<p>Pesan dikirim setiap status berubah, dan saat alat berhenti mengirim data lebih dari 60 detik.</p>""",
"saat kamu memicu status waspada di alat, pesan masuk ke Telegram dalam beberapa detik.")}

{langkah(10, "Pasang di lapangan", "Lihat panduan perakitan", """
<p>Setelah semuanya bekerja di meja, lanjutkan ke <code>docs/panduan-perakitan.md</code>: pemindahan ke PCB, catu daya panel surya, box tahan air, dan pemasangan di lereng.</p>
<p>Di lereng, alat butuh WiFi untuk mengirim data: router atau modem 4G di dekat lokasi, atau hotspot HP yang ditinggal.
Kalau lokasinya tanpa sinyal, alat tetap berfungsi sebagai alarm lokal lewat LED dan buzzer.</p>
<div class="warn">Minta izin pemilik lahan, beri tahu warga atau perangkat desa, jangan memasang saat hujan, dan pergi minimal berdua.</div>""",
"alat terpasang tegak di tiang, LED hijau menyala setelah tombol kalibrasi ditekan, dan dashboard menerima data dari lokasi.")}

<section class="page">
  <h2 class="big">Kalau ada masalah</h2>
  <table class="trouble">
    <tr><th>Gejala</th><th>Penyebab paling sering</th><th>Cara mengatasi</th></tr>
    <tr><td>Upload berhenti di <code>Connecting.....</code></td><td>ESP32 belum masuk mode upload</td><td>Tahan tombol BOOT sampai upload berjalan</td></tr>
    <tr><td>Port COM tidak muncul</td><td>Driver belum terpasang, atau kabel hanya untuk cas</td><td>Pasang driver CP210x atau CH340. Coba kabel lain</td></tr>
    <tr><td><code>MPU6050 tidak terdeteksi</code></td><td>SDA dan SCL tertukar, atau kabel longgar</td><td>SDA ke GPIO 21, SCL ke GPIO 22, VCC ke 3V3</td></tr>
    <tr><td>LED tidak menyala</td><td>LED terbalik</td><td>Kaki panjang ke resistor, kaki pendek ke GND</td></tr>
    <tr><td><code>soil_raw</code> / <code>rain_raw</code> tidak berubah</td><td>Kabel sinyal salah pin</td><td>Tanah ke GPIO 34, hujan ke GPIO 35 (pin AO)</td></tr>
    <tr><td>Persen terbalik (basah = 0%)</td><td>Nilai kering dan basah tertukar</td><td>Tukar kedua angka di <code>config.h</code></td></tr>
    <tr><td>Langsung waspada padahal diam</td><td>Patokan diambil saat alat masih bergerak</td><td>Diamkan alat, tekan tombol kalibrasi</td></tr>
    <tr><td>Backend: <code>could not open port</code></td><td>Port dipakai Monitor, atau nomor salah</td><td>Tutup Monitor. Cek Device Manager</td></tr>
    <tr><td>Dashboard: "Alat tidak mengirim data"</td><td>ESP32 belum tersambung ke backend</td><td>USB: cek <code>SERIAL_PORT</code>. WiFi: cek <code>SERVER_URL</code> dan firewall</td></tr>
    <tr><td><code>kirim_gagal</code>, <code>"http":-1</code></td><td>ESP32 tidak menjangkau laptop</td><td>WiFi sama, IP benar, backend pakai <code>--host 0.0.0.0</code></td></tr>
    <tr><td><code>kirim_gagal</code>, <code>"http":401</code></td><td>Kunci API berbeda</td><td>Samakan <code>API_KEY</code> di <code>secrets.h</code> dan backend</td></tr>
    <tr><td>Tidak pernah muncul event <code>wifi</code></td><td>Nama/sandi WiFi salah, atau WiFi 5 GHz</td><td>Periksa <code>secrets.h</code>. Pakai 2,4 GHz</td></tr>
  </table>
</section>

<section class="page">
  <h2 class="big">Kamus singkat</h2>
  <table>
    <tr><th>Istilah</th><th>Arti</th></tr>
    <tr><td>Firmware</td><td>Program yang ditanam di dalam ESP32</td></tr>
    <tr><td>Upload / flash</td><td>Mengirim firmware dari laptop ke ESP32</td></tr>
    <tr><td>GPIO</td><td>Kaki ESP32 yang bisa membaca atau mengendalikan sesuatu</td></tr>
    <tr><td>ADC</td><td>Bagian ESP32 yang mengubah tegangan sensor menjadi angka 0–4095</td></tr>
    <tr><td>I2C</td><td>Cara komunikasi dua kabel (SDA dan SCL) yang dipakai MPU6050</td></tr>
    <tr><td>Serial Monitor</td><td>Jendela untuk membaca teks yang dikirim ESP32 lewat USB</td></tr>
    <tr><td>JSON</td><td>Format teks data, contoh <code>{{"status":"aman","soil_pct":20}}</code></td></tr>
    <tr><td>Backend</td><td>Program di laptop atau server yang menerima dan menyimpan data</td></tr>
    <tr><td>Dashboard</td><td>Halaman web untuk memantau data</td></tr>
    <tr><td>Telemetri</td><td>Data pengukuran yang dikirim alat secara berkala</td></tr>
    <tr><td>Kalibrasi</td><td>Menyesuaikan pembacaan alat dengan kondisi sebenarnya</td></tr>
  </table>
  <div class="end">
    <p><b>Dokumen terkait di repositori</b></p>
    <p><code>docs/panduan-perakitan.md</code> · versi lapangan dengan panel surya dan box IP65<br>
    <code>docs/RAB_SIARENG_hemat.xlsx</code> · daftar belanja uji<br>
    <code>docs/simulasi-demo.md</code> · skenario demo di kelas<br>
    <code>backend-api/README.md</code> · pengaturan server</p>
  </div>
</section>
'''

CSS = """
@page { size: A4; margin: 16mm 16mm 18mm; }
* { box-sizing: border-box; }
body { margin: 0; font-family: "Segoe UI", system-ui, -apple-system, sans-serif; color: #1d1d1f; font-size: 10.5pt; line-height: 1.5; }
h1, h2, h3, h4 { margin: 0; font-weight: 600; letter-spacing: -0.02em; }
p { margin: 0 0 8px; }
code { font-family: Consolas, "SF Mono", monospace; font-size: 9pt; background: #f0f0f2; padding: 1px 5px; border-radius: 4px; }
pre { font-family: Consolas, monospace; font-size: 9pt; background: #1d1d1f; color: #f5f5f7; padding: 10px 14px; border-radius: 10px; margin: 6px 0 10px; white-space: pre-wrap; }
table { width: 100%; border-collapse: collapse; margin: 8px 0 12px; font-size: 9.5pt; }
th { text-align: left; font-weight: 600; color: #6e6e73; border-bottom: 1.5px solid #d2d2d7; padding: 6px 8px; }
td { border-bottom: 1px solid #e8e8ed; padding: 6px 8px; vertical-align: top; }
ol, ul { margin: 4px 0 10px; padding-left: 20px; } li { margin: 3px 0; }
.small { font-size: 9pt; color: #6e6e73; }
.cover { height: 260mm; display: flex; flex-direction: column; justify-content: center; page-break-after: always; }
.eyebrow { color: #6e6e73; font-size: 11pt; }
.cover h1 { font-size: 46pt; line-height: 1.02; letter-spacing: -0.035em; margin: 8px 0 16px; }
.lead { font-size: 15pt; color: #3a3a3c; line-height: 1.35; }
.cover-art { display: flex; gap: 10px; margin: 36px 0; }
.cover-art figure { flex: 1; margin: 0; background: #f5f5f7; border-radius: 16px; padding: 12px 10px 10px; }
.cover-art figcaption { text-align: center; font-weight: 600; margin-top: 6px; }
.cover-foot { margin-top: auto; color: #6e6e73; font-size: 9pt; }
.scene { width: 100%; display: block; }
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; vertical-align: 0; }
.dot.g { background: #2a9d4b; } .dot.y { background: #e6a100; } .dot.r { background: #e0302a; }
.page { page-break-before: always; }
.big { font-size: 24pt; margin-bottom: 14px; }
h3 { font-size: 12.5pt; margin: 14px 0 6px; }
.note { background: #e6f1fb; border-radius: 12px; padding: 10px 14px; margin: 12px 0; }
.warn { background: #fff4e5; border-radius: 12px; padding: 10px 14px; margin: 12px 0; }
.ok { background: #e9f6ec; border-radius: 12px; padding: 9px 14px; margin: 10px 0 4px; break-inside: avoid; }
.ok b { color: #1e7a3a; margin-right: 4px; }
.flow { padding-left: 20px; }
.grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; }
.card { background: #f5f5f7; border-radius: 12px; padding: 10px 12px; }
.card h4 { font-size: 10pt; margin-bottom: 4px; } .card p { font-size: 8.8pt; margin: 0 0 4px; }
.card .ana { color: #0066cc; font-weight: 600; }
.step { page-break-before: always; }
.step-head { display: flex; gap: 14px; align-items: center; margin-bottom: 12px; }
.num { width: 46px; height: 46px; border-radius: 50%; background: #1d1d1f; color: #fff; font-size: 20pt; font-weight: 600; display: flex; align-items: center; justify-content: center; flex: none; }
.step h2 { font-size: 20pt; } .meta { color: #6e6e73; margin: 0; font-size: 9.5pt; }
.substep { break-inside: avoid; margin: 0 0 18px; padding-top: 6px; border-top: 1px solid #e8e8ed; }
.substep h3 { font-size: 13.5pt; margin: 6px 0 8px; display: flex; align-items: center; gap: 10px; }
.snum { background: #0066cc; color: #fff; border-radius: 8px; padding: 1px 8px; font-size: 10pt; }
.dg { width: 100%; display: block; margin: 6px 0; }
.dg text { font-family: "Segoe UI", system-ui, sans-serif; }
.lbl { font-size: 13px; font-weight: 600; fill: #1d1d1f; }
.sub { font-size: 11px; fill: #6e6e73; }
.chip-t { font-size: 13px; font-weight: 600; fill: #22262b; }
.dg .chip-t[transform] { fill: #f5f5f7; }
.pin-e { font-size: 11.5px; font-weight: 600; fill: #f5f5f7; }
.pin-k { font-size: 11.5px; fill: #1d1d1f; }
.cap { font-size: 8.8pt; color: #6e6e73; margin-top: 2px; }
.trouble td:first-child { width: 30%; }
.end { margin-top: 24px; background: #f5f5f7; border-radius: 12px; padding: 12px 14px; }
"""

HTML.write_text(f"""<!doctype html><html lang="id"><head><meta charset="utf-8">
<title>Panduan membuat SIARENG</title><style>{CSS}</style></head><body>{body}</body></html>""", encoding="utf-8")


def cari_browser():
    for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if os.path.exists(p):
            return p
    return shutil.which("msedge") or shutil.which("google-chrome") or shutil.which("chromium")


b = cari_browser()
if not b:
    sys.exit(f"HTML dibuat di {HTML}, tetapi Edge/Chrome tidak ditemukan untuk mencetak PDF.")
subprocess.run([b, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={PDF}", HTML.as_uri()], check=True, capture_output=True, timeout=120)
print(f"PDF dibuat: {PDF}")
