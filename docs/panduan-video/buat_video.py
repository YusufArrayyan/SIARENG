"""Video animasi panduan merakit SIARENG (1920x1080, 25 fps, tanpa suara, dengan teks keterangan).

Jalankan dari folder proyek:
    python docs/panduan-video/buat_video.py              -> docs/Video_Panduan_SIARENG.mp4
    python docs/panduan-video/buat_video.py --cek 12 40  -> simpan bingkai detik 12 dan 40 sebagai PNG
Butuh: Pillow, dan ffmpeg (pip install imageio-ffmpeg, atau ffmpeg di PATH).
"""
import math
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "Video_Panduan_SIARENG.mp4"
FPS = 25
W, H = 1280, 720          # koordinat logis
S = 2                     # digambar 2x lalu diperkecil agar halus
OW, OH = 1920, 1080       # ukuran keluaran

BG = (245, 245, 247)
CARD = (255, 255, 255)
INK = (29, 29, 31)
INK2 = (110, 110, 115)
HAIR = (210, 210, 215)
BLUE = (0, 102, 204)
GRN = (42, 157, 75)
YEL = (230, 161, 0)
RED = (224, 48, 42)
DARK = (34, 38, 43)
PURP = (138, 79, 216)
TEAL = (22, 160, 133)
WIRE = {"3V3": RED, "GND": INK, "SDA": (47, 125, 225), "SCL": YEL, "SIG": PURP, "ADC": TEAL}

FONTS = {"r": "segoeui.ttf", "b": "segoeuib.ttf", "sb": "seguisb.ttf", "m": "consola.ttf", "l": "segoeuil.ttf"}


@lru_cache(None)
def font(size, w="r"):
    return ImageFont.truetype(f"C:/Windows/Fonts/{FONTS[w]}", int(size * S))


# ------------------------------------------------------------------ bantuan gambar
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def prog(t, start, dur):
    return ease((t - start) / dur) if dur > 0 else float(t >= start)


def mix(c, bg, a):
    a = clamp(a)
    return tuple(int(bg[i] + (c[i] - bg[i]) * a) for i in range(3))


class Pen:
    def __init__(self, img):
        self.d = ImageDraw.Draw(img)
        self.bg = BG

    def rr(self, x, y, w, h, r, fill=None, outline=None, width=1, a=1.0):
        self.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=r * S,
                                 fill=mix(fill, self.bg, a) if fill else None,
                                 outline=mix(outline, self.bg, a) if outline else None, width=int(width * S))

    def circle(self, cx, cy, r, fill=None, outline=None, width=1, a=1.0):
        self.d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S],
                       fill=mix(fill, self.bg, a) if fill else None,
                       outline=mix(outline, self.bg, a) if outline else None, width=int(width * S))

    def line(self, pts, color, width=2, a=1.0):
        self.d.line([(x * S, y * S) for x, y in pts], fill=mix(color, self.bg, a), width=int(width * S), joint="curve")

    def poly(self, pts, fill, a=1.0):
        self.d.polygon([(x * S, y * S) for x, y in pts], fill=mix(fill, self.bg, a))

    def text(self, x, y, s, size, color=INK, w="r", anchor="la", a=1.0, bg=None):
        self.d.text((x * S, y * S), s, font=font(size, w), fill=mix(color, bg or self.bg, a), anchor=anchor)

    def tw(self, s, size, w="r"):
        return self.d.textlength(s, font=font(size, w)) / S

    def wrap(self, s, size, maxw, w="r"):
        out, cur = [], ""
        for word in s.split():
            nxt = (cur + " " + word).strip()
            if self.tw(nxt, size, w) <= maxw:
                cur = nxt
            else:
                out.append(cur)
                cur = word
        if cur:
            out.append(cur)
        return out

    def para(self, x, y, s, size, maxw, color=INK, w="r", lh=1.35, a=1.0, anchor="la", bg=None):
        for i, ln in enumerate(self.wrap(s, size, maxw, w)):
            self.text(x, y + i * size * lh, ln, size, color, w, anchor, a, bg)
        return len(self.wrap(s, size, maxw, w)) * size * lh


def bezier(p0, p1, p2, p3, n=40, upto=1.0):
    pts = []
    m = max(2, int(n * upto))
    for i in range(m + 1):
        t = upto * i / m
        u = 1 - t
        pts.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return pts


def rot(px, py, cx, cy, deg):
    a = math.radians(deg)
    dx, dy = px - cx, py - cy
    return cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)


# ------------------------------------------------------------------ objek berulang
def lereng(p, x, y, sc, t, soil=0.2, rain=0.0, tilt=0.0, led=GRN, a=1.0):
    """Ilustrasi lereng + tiang alat. (x, y) = pojok kiri atas, kotak 300x200 dikali sc."""
    P = lambda px, py: (x + px * sc, y + py * sc)
    # hujan
    if rain > 0.01:
        for i in range(16):
            bx = (i * 47) % 300
            by = ((i * 29) % 70 + (t * 140) % 70) % 70
            p.line([P(bx + 6, by), P(bx, by + 16)], (55, 138, 221), 2.2, a * rain)
    ground = mix((154, 122, 78), (220, 207, 180), clamp(soil))
    p.poly([P(0, 172), P(300, 84), P(300, 200), P(0, 200)], ground, a)
    p.line([P(0, 172), P(300, 84)], (90, 80, 70), 2.5, a)
    p.line([P(170, 122), P(170, 52)], (170, 170, 170), 1.5, a * 0.8)
    c = (170, 122)
    R = lambda px, py: P(*rot(px, py, c[0], c[1], tilt))
    p.line([R(170, 140), R(170, 60)], INK, 5 * sc / 1.6, a)
    box = [R(155, 62), R(185, 62), R(185, 86), R(155, 86)]
    p.poly(box, CARD, a)
    p.line(box + [box[0]], INK, 2.2, a)
    lx, ly = R(170, 74)
    p.circle(lx, ly, 5 * sc / 1.4, led, a=a)
    p.line([R(150, 54), R(190, 46)], INK, 5 * sc / 1.6, a)
    p.line(bezier(P(185, 82), P(206, 86), P(214, 96), P(214, 112)) + [P(214, 126)], (90, 90, 90), 1.6, a)


def esp32(p, x, y, w, h, a=1.0, label=True):
    p.rr(x, y, w, h, 16, DARK, a=a)
    if not label:
        return
    p.rr(x + w / 2 - 50, y + h / 2 - 42, 100, 70, 6, (184, 188, 194), a=a)
    if label:
        p.text(x + w / 2, y + h / 2 - 7, "ESP32", 20, DARK, "sb", "mm", a, bg=(184, 188, 194))
    p.rr(x + w / 2 - 20, y + h - 22, 40, 16, 3, (141, 144, 150), a=a)


def kartu_cek(p, x, y, w, s, a):
    """Kotak hijau 'Berhasil kalau'."""
    if a <= 0:
        return
    h = 56 + len(p.wrap(s, 19, w - 76)) * 26
    p.rr(x, y, w, h, 16, (233, 246, 236), a=a)
    p.circle(x + 30, y + 30, 13, GRN, a=a)
    p.line([(x + 23, y + 30), (x + 28, y + 36), (x + 38, y + 24)], CARD, 3, a)
    p.text(x + 56, y + 18, "Berhasil kalau", 15, (30, 122, 58), "sb", a=a, bg=(233, 246, 236))
    p.para(x + 56, y + 40, s, 19, w - 76, INK, a=a, bg=(233, 246, 236))


# ------------------------------------------------------------------ adegan
SCENES = []


def scene(dur, chip=""):
    def deco(fn):
        SCENES.append((dur, chip, fn))
        return fn
    return deco


def judul(p, t, teks, sub=None, y=70):
    a = prog(t, 0, 0.5)
    p.text(80, y - 10 * (1 - a), teks, 44, INK, "sb", a=a)
    if sub:
        p.text(82, y + 62, sub, 22, INK2, a=prog(t, 0.2, 0.5))


@scene(6)
def s_sampul(p, t):
    a = prog(t, 0, 0.8)
    p.text(80, 120, "Teknologi IoT · Informatika UNIB", 22, INK2, a=a)
    p.text(76, 160 + 20 * (1 - a), "Panduan membuat", 64, INK, "sb", a=a)
    p.text(76, 240 + 20 * (1 - a), "SIARENG", 96, INK, "b", a=prog(t, 0.3, 0.8))
    p.para(80, 380, "Alat pemantau potensi longsor lereng berbasis ESP32. Dari komponen lepas sampai data tampil di dashboard.",
           24, 520, INK2, a=prog(t, 0.8, 0.8))
    k = clamp((t - 1.5) / 4)
    soil, rain, tilt = 0.2 + 0.7 * k, clamp(k * 2), 16 * clamp((k - 0.5) * 2)
    led = GRN if k < 0.35 else YEL if k < 0.75 else RED
    p.rr(700, 150, 500, 380, 28, CARD, a=prog(t, 0.4, 0.8))
    lereng(p, 735, 200, 1.45, t, soil, rain, tilt, led, a=prog(t, 0.6, 0.8))


@scene(14, "Gambaran")
def s_alur(p, t):
    judul(p, t, "Cara kerja SIARENG")
    boxes = [
        (80, 230, 230, "3 sensor", "tanah · hujan · kemiringan", (245, 245, 247)),
        (420, 230, 200, "ESP32", "memutuskan status", (230, 241, 251)),
        (730, 230, 220, "Laptop", "backend menyimpan data", (245, 245, 247)),
        (1040, 180, 170, "Dashboard", "laptop / HP", (245, 245, 247)),
        (1040, 300, 170, "Telegram", "opsional", (245, 245, 247)),
        (420, 420, 200, "LED + buzzer", "alarm di lokasi", (255, 244, 229)),
    ]
    starts = [0.6, 1.8, 3.6, 5.2, 5.6, 2.6]
    for (x, y, w, tt, ss, f), st in zip(boxes, starts):
        a = prog(t, st, 0.6)
        p.rr(x, y + 10 * (1 - a), w, 90, 18, f, HAIR, 1.5, a)
        p.text(x + w / 2, y + 36 + 10 * (1 - a), tt, 24, INK, "sb", "mm", a, bg=f)
        p.text(x + w / 2, y + 66 + 10 * (1 - a), ss, 16, INK2, anchor="mm", a=a, bg=f)
    arrows = [((310, 275), (418, 275), 1.4), ((520, 320), (520, 418), 2.3), ((620, 275), (728, 275), 3.1),
              ((950, 255), (1038, 225), 4.8), ((950, 295), (1038, 345), 5.0)]
    for (a0, a1, st) in arrows:
        k = prog(t, st, 0.5)
        if k > 0:
            e = (a0[0] + (a1[0] - a0[0]) * k, a0[1] + (a1[1] - a0[1]) * k)
            p.line([a0, e], BLUE, 3)
            if k > 0.95:
                ang = math.atan2(a1[1] - a0[1], a1[0] - a0[0])
                p.poly([a1, (a1[0] - 12 * math.cos(ang - .45), a1[1] - 12 * math.sin(ang - .45)),
                        (a1[0] - 12 * math.cos(ang + .45), a1[1] - 12 * math.sin(ang + .45))], BLUE)
    p.text(674, 258, "USB / WiFi", 15, BLUE, "sb", "mm", a=prog(t, 3.3, 0.5))
    # paket data berjalan
    if t > 6:
        for i in range(3):
            k = ((t - 6) * 0.6 + i / 3) % 1
            x = 310 + (728 - 310) * k
            if not 600 < x < 640:
                p.circle(x, 275, 6, BLUE)


@scene(18, "Gambaran")
def s_status(p, t):
    judul(p, t, "Tiga tingkat status")
    fases = [(0, "Aman", GRN, "Tanah dan kemiringan dalam batas normal.", 0.2, 0, 0),
             (6, "Waspada", YEL, "Tanah jenuh (≥ 80%), atau lereng bergeser ≥ 2°, atau tanah basah saat hujan deras.", 0.85, 0.9, 6),
             (12, "Bahaya", RED, "Tanah jenuh DAN lereng bergeser ≥ 5°. Jauhi area lereng.", 1.0, 1.0, 16)]
    cur = [f for f in fases if t >= f[0]][-1]
    prev = fases[max(0, fases.index(cur) - 1)]
    k = prog(t, cur[0], 1.5)
    soil = prev[4] + (cur[4] - prev[4]) * k
    rain = prev[5] + (cur[5] - prev[5]) * k
    tilt = prev[6] + (cur[6] - prev[6]) * k
    p.rr(80, 170, 560, 420, 28, CARD)
    lereng(p, 110, 210, 1.65, t, soil, rain, tilt, cur[2])
    blink = cur[1] != "Bahaya" or int(t * 4) % 2 == 0
    for i, (st, nm, col, ds, *_r) in enumerate(fases):
        y = 190 + i * 130
        on = nm == cur[1]
        f = mix(col, CARD, 0.12) if on else CARD
        p.rr(690, y, 510, 112, 20, f, col if on else HAIR, 2.5 if on else 1.2)
        p.circle(728, y + 34, 11, col if (on and blink) or not on else mix(col, f, 0.25), a=1 if on else 0.35)
        p.text(752, y + 18, nm, 28, col if on else INK2, "sb", bg=f)
        p.para(710, y + 56, ds, 17, 470, INK if on else INK2, bg=f)
    p.text(80, 610, "Status naik setelah kondisi bertahan 2 detik dan turun setelah 6 detik, supaya tidak ada alarm palsu.", 17, INK2,
           a=prog(t, 3, 0.6))


KOMPONEN = [("ESP32", "Otak alat", "Membaca sensor, memutuskan status"),
            ("MPU6050", "Waterpas digital", "Mengukur kemiringan"),
            ("Sensor tanah", "Jari di dalam tanah", "Mengukur seberapa basah tanah"),
            ("Sensor hujan", "Telapak penadah hujan", "Mendeteksi air di panel"),
            ("3 LED", "Lampu lalu lintas", "Menunjukkan status"),
            ("Buzzer", "Peluit", "Bunyi peringatan"),
            ("Tombol", "Tombol nol timbangan", "Menetapkan posisi normal"),
            ("Breadboard", "Papan colok", "Menyambung tanpa solder")]


@scene(14, "Komponen")
def s_komponen(p, t):
    judul(p, t, "Kenali komponennya", "Rp210.000 untuk versi uji. Daftar belanja ada di RAB_SIARENG_hemat.xlsx")
    for i, (nm, ana, ds) in enumerate(KOMPONEN):
        cx, cy = 80 + (i % 4) * 285, 220 + (i // 4) * 220
        a = prog(t, 0.8 + i * 0.6, 0.6)
        p.rr(cx, cy + 14 * (1 - a), 265, 195, 22, CARD, HAIR, 1, a)
        p.text(cx + 22, cy + 26, nm, 26, INK, "sb", a=a, bg=CARD)
        p.text(cx + 22, cy + 70, ana, 19, BLUE, "sb", a=a, bg=CARD)
        p.para(cx + 22, cy + 110, ds, 17, 225, INK2, a=a, bg=CARD)


@scene(11, "Langkah 1–3")
def s_laptop(p, t):
    judul(p, t, "Langkah 1–3: siapkan laptop", "Bisa dikerjakan sebelum komponen datang")
    items = [("Visual Studio Code", "code.visualstudio.com"), ("Git", "git-scm.com"),
             ("Python 3.10+", "centang “Add python.exe to PATH”"), ("Ekstensi PlatformIO IDE", "di VS Code, menu Extensions"),
             ("Ekstensi Wokwi Simulator", "F1 → Wokwi: Request a New License"), ("Ambil kode", "git clone github.com/YusufArrayyan/SIARENG")]
    for i, (a1, b1) in enumerate(items):
        y = 220 + i * 70
        a = prog(t, 0.8 + i * 1.1, 0.5)
        p.rr(80, y, 740, 56, 16, CARD, a=a)
        done = t > 1.4 + i * 1.1
        p.circle(118, y + 28, 15, GRN if done else HAIR, a=a)
        if done:
            p.line([(110, y + 28), (116, y + 35), (127, y + 21)], CARD, 3)
        p.text(150, y + 12, a1, 21, INK, "sb", a=a, bg=CARD)
        p.text(470, y + 16, b1, 16, INK2, a=a, bg=CARD)
    p.rr(870, 220, 330, 400, 24, CARD, a=prog(t, 2, 0.6))
    p.text(900, 248, "Lalu coba dulu tanpa alat", 19, INK, "sb", a=prog(t, 2, 0.6), bg=CARD)
    p.para(900, 290, "Simulasi Wokwi: buka folder firmware, Build, lalu F1 → Wokwi: Start Simulator.", 17, 280, INK2,
           a=prog(t, 2.4, 0.6), bg=CARD)
    p.para(900, 400, "Dashboard demo: klik dua kali dashboard/index.html, lalu tekan “Lereng bergerak”.", 17, 280, INK2,
           a=prog(t, 3, 0.6), bg=CARD)
    lereng(p, 920, 490, 0.75, t, 0.9, 0.8, 14 * prog(t, 5, 2), YEL if t < 6.5 else RED, a=prog(t, 3.5, 0.6))


@scene(13, "Langkah 5")
def s_breadboard(p, t):
    judul(p, t, "Langkah 5: kenali breadboard", "Pasang satu komponen, uji, baru pasang berikutnya")
    p.rr(80, 200, 1120, 330, 20, (241, 239, 232), (201, 198, 187), 2)
    for yy, c in ((222, RED), (240, (47, 125, 225)), (490, RED), (508, (47, 125, 225))):
        p.line([(110, yy), (1170, yy)], c, 2)
    p.rr(95, 358, 1090, 14, 2, (221, 217, 204))
    for col in range(42):
        x = 120 + col * 25
        for r in range(5):
            p.rr(x - 4, 270 + r * 17 - 4, 8, 8, 1.5, (85, 82, 74))
            p.rr(x - 4, 385 + r * 17 - 4, 8, 8, 1.5, (85, 82, 74))
    k1, k2, k3 = prog(t, 1.5, 0.6), prog(t, 4.5, 0.6), prog(t, 7.5, 0.6)
    if k1:
        p.rr(258, 258, 24, 88, 6, None, BLUE, 3, k1)
        p.para(80, 560, "Lima lubang dalam satu kolom pendek saling tersambung.", 22, 1100, INK, a=k1 * (1 - k2))
    if k2:
        p.rr(102, 214, 1076, 34, 8, None, BLUE, 3, k2)
        p.para(80, 560, "Jalur panjang di tepi tersambung sepanjang papan: merah = 3V3 (+), biru = GND (−).", 22, 1100, INK, a=k2 * (1 - k3))
    if k3:
        p.para(80, 560, "Celah di tengah memisahkan atas dan bawah. ESP32 dan tombol dipasang melintang di atas celah ini.",
               22, 1100, INK, a=k3)
        p.rr(95, 358, 1090, 14, 2, None, BLUE, 3, k3)
    p.text(80, 640, "Cabut USB setiap mengubah sambungan · Sensor dapat daya dari pin 3V3, bukan 5V", 18, RED, "sb",
           a=prog(t, 9.5, 0.6))


def adegan_kabel(judul_, pins, komp, saran, cek):
    def fn(p, t):
        judul(p, t, judul_)
        n = len(pins)
        row = 62
        y0 = 360 - (n - 1) * row / 2
        a = prog(t, 0.3, 0.6)
        esp32(p, 80, 190, 300, 340, a)
        p.rr(830, y0 - 50, 370, (n - 1) * row + 100, 22, CARD, HAIR, 1.5, a)
        p.text(1015, y0 - 72, komp, 22, INK, "sb", "mm", a)
        for i, (pe, pk, w) in enumerate(pins):
            y = y0 + i * row
            col = WIRE.get(w, w) if isinstance(w, str) else w
            st = 1.2 + i * 0.9
            k = prog(t, st, 0.8)
            p.circle(380, y, 8, (217, 180, 74), DARK, 2.5, a)
            p.text(362, y, pe, 19, (245, 245, 247), "sb", "rm", a, bg=DARK)
            if k > 0:
                p.line(bezier((388, y), (560, y), (650, y), (822, y), 50, k), col, 7)
            p.circle(830, y, 8, CARD, col, 3, a)
            p.text(852, y, pk, 19, INK, anchor="lm", a=prog(t, st + 0.5, 0.4), bg=CARD)
        tsar = 1.6 + n * 0.9
        p.para(80, 560, saran, 19, 720, INK2, a=prog(t, tsar, 0.6))
        kartu_cek(p, 830, y0 + (n - 1) * row + 70, 370, cek, prog(t, tsar + 2.2, 0.6))
    return fn


KABEL = [
    ("5.1  ESP32 saja", [("3V3", "Jalur merah (+)", "3V3"), ("GND", "Jalur biru (−)", "GND")], "Breadboard",
     "Ubah SIMULASI ke 0 di config.h, lalu PlatformIO → Upload dan Monitor. Kalau macet di “Connecting…”, tahan tombol BOOT.",
     "Monitor menampilkan event boot. Pesan “MPU6050 tidak terdeteksi” masih wajar."),
    ("5.2  MPU6050 (kemiringan)", [("3V3", "VCC", "3V3"), ("GND", "GND", "GND"), ("GPIO 21", "SDA", "SDA"), ("GPIO 22", "SCL", "SCL")],
     "MPU6050", "Tekan tombol EN di ESP32 untuk memulai ulang setelah memasang sensor.",
     "Muncul baseline_siap, dan nilai tilt naik saat breadboard dimiringkan."),
    ("5.3  Tiga LED", [("GPIO 26", "resistor → LED hijau", GRN), ("GPIO 27", "resistor → LED kuning", YEL),
                       ("GPIO 14", "resistor → LED merah", RED), ("GND", "kaki pendek LED", "GND")],
     "3 LED + resistor", "Kaki panjang LED ke resistor, kaki pendek ke GND. LED terbalik tidak rusak, hanya tidak menyala.",
     "LED kuning 2 detik saat mulai, lalu hijau. Dimiringkan > 2°: kuning."),
    ("5.4  Buzzer", [("GPIO 25", "S (sinyal)", "SIG"), ("GND", "− / GND", "GND"), ("3V3", "+ (kalau ada)", "3V3")],
     "Buzzer pasif", "Buzzer pasif dibunyikan dengan nada dari ESP32, jadi jangan diganti buzzer aktif tanpa mengubah config.h.",
     "Bip pendek tiap 3 detik saat status waspada."),
    ("5.5  Tombol kalibrasi", [("GPIO 15", "kaki 1", (95, 107, 122)), ("GND", "kaki diagonal", "GND")], "Push button",
     "Tombol dipasang melintang di celah tengah. Pakai dua kaki yang berseberangan diagonal.",
     "Menekan tombol memunculkan kalibrasi_ulang, dan LED kembali hijau."),
    ("5.6  Sensor tanah", [("3V3", "VCC", "3V3"), ("GND", "GND", "GND"), ("GPIO 34", "AOUT", "ADC")], "Sensor tanah kapasitif",
     "Yang boleh basah hanya bagian di bawah garis putih. Komponen di atasnya harus tetap kering.",
     "Nilai soil_raw berubah saat sensor digenggam atau dicelup air."),
    ("5.7  Sensor hujan", [("3V3", "VCC", "3V3"), ("GND", "GND", "GND"), ("GPIO 35", "AO (bukan DO)", "ADC")], "Modul sensor hujan",
     "Panel bergaris disambung ke modul kecil dengan dua kabel bawaannya. Pin DO tidak dipakai.",
     "Nilai rain_raw turun saat panel ditetesi air. Rangkaian lengkap."),
]
for _k in KABEL:
    scene(9.5 + len(_k[1]) * 0.9, "Langkah 5")(adegan_kabel(*_k))


@scene(14, "Langkah 5")
def s_peta(p, t):
    judul(p, t, "Peta sambungan lengkap", "Simpan gambar ini di samping breadboard")
    rows = [("3V3", "VCC semua sensor", RED), ("GND", "GND semua komponen", INK), ("GPIO 21", "MPU6050 · SDA", WIRE["SDA"]),
            ("GPIO 22", "MPU6050 · SCL", WIRE["SCL"]), ("GPIO 34", "Sensor tanah · AOUT", TEAL), ("GPIO 35", "Sensor hujan · AO", TEAL),
            ("GPIO 26", "LED hijau (lewat resistor)", GRN), ("GPIO 27", "LED kuning (lewat resistor)", YEL),
            ("GPIO 14", "LED merah (lewat resistor)", RED), ("GPIO 25", "Buzzer · S", PURP), ("GPIO 15", "Tombol (kaki lain ke GND)", (95, 107, 122))]
    esp32(p, 80, 180, 220, 500, label=False)
    p.text(100, 650, "ESP32", 22, (161, 161, 166), "sb", "lm", bg=DARK)
    for i, (pe, ds, col) in enumerate(rows):
        y = 205 + i * 44
        a = prog(t, 0.6 + i * 0.45, 0.4)
        p.circle(300, y, 7, (217, 180, 74), DARK, 2)
        p.text(285, y, pe, 17, (245, 245, 247), "sb", "rm", bg=DARK)
        if a:
            p.line([(308, y), (308 + 290 * a, y)], col, 6)
            p.rr(610, y - 18, 540, 36, 10, CARD, HAIR, 1, a)
            p.text(630, y, ds, 18, INK, anchor="lm", a=a, bg=CARD)


@scene(16, "Langkah 6")
def s_kalibrasi(p, t):
    judul(p, t, "Langkah 6: kalibrasi sensor", "Setiap sensor sedikit berbeda. Catat angka kering dan basah milikmu.")
    p.rr(80, 200, 560, 400, 22, (29, 29, 31))
    p.text(104, 222, "Serial Monitor", 15, (161, 161, 166), bg=(29, 29, 31))
    kering = t < 7
    raw = int(3180 + 20 * math.sin(t * 3)) if kering else int(1420 + 15 * math.sin(t * 3))
    for i in range(min(9, int(t * 1.5))):
        rr = raw - (8 - i) * 3
        p.text(104, 260 + i * 36, f'{{"soil_raw":{rr},"rain_raw":4091}}', 18, (152, 220, 152), "m", bg=(29, 29, 31))
    # sensor + gelas
    gx = 760
    p.rr(gx + 4, 420, 152, 136, 14, (200, 225, 245))          # air dalam gelas
    p.rr(gx, 330, 160, 230, 18, None, (150, 160, 170), 3)
    sy = 120 + (150 * prog(t, 7, 1) if not kering else 0)      # garis putih berhenti tepat di permukaan air
    p.rr(gx + 60, sy, 40, 260, 6, (40, 40, 44))
    p.line([(gx + 60, sy + 150), (gx + 100, sy + 150)], CARD, 2)
    p.text(gx + 80, 600, "di udara" if kering else "dicelup air sampai garis putih", 18, INK2, anchor="mm")
    p.rr(980, 260, 220, 240, 20, CARD, a=prog(t, 1, 0.5))
    p.text(1000, 285, "config.h", 18, INK2, "m", bg=CARD, a=prog(t, 1, 0.5))
    p.text(1000, 330, "SOIL_RAW_KERING", 17, INK, "m", bg=CARD, a=prog(t, 4, 0.5))
    p.text(1000, 356, "= 3180", 22, BLUE, "m", bg=CARD, a=prog(t, 5, 0.5))
    p.text(1000, 410, "SOIL_RAW_BASAH", 17, INK, "m", bg=CARD, a=prog(t, 10, 0.5))
    p.text(1000, 436, "= 1420", 22, BLUE, "m", bg=CARD, a=prog(t, 11, 0.5))
    p.text(80, 640, "Ulangi untuk sensor hujan: panel kering lalu panel basah. Isi keempat angka, lalu Upload lagi.", 18, INK,
           a=prog(t, 12, 0.6))


def dashboard_mock(p, x, y, w, status, soil, rain, tilt, a=1.0):
    col = {"Aman": GRN, "Waspada": YEL, "Bahaya": RED}[status]
    hb = {"Aman": (233, 246, 236), "Waspada": (255, 244, 229), "Bahaya": (29, 29, 31)}[status]
    p.rr(x, y, w, 360, 22, CARD, HAIR, 1.5, a)
    p.rr(x + 18, y + 18, w - 36, 150, 18, hb, a=a)
    p.text(x + 44, y + 44, "Lereng uji · esp32-longsor-lereng01", 14, INK2 if status != "Bahaya" else (200, 200, 205), a=a, bg=hb)
    p.text(x + 42, y + 72, status, 46, col, "sb", a=a, bg=hb)
    for i, (nm, v, u) in enumerate((("Tanah", soil, "%"), ("Hujan", rain, "%"), ("Kemiringan", tilt, "°"))):
        cx = x + 18 + i * (w - 36) / 3
        p.rr(cx + 4, y + 184, (w - 36) / 3 - 8, 150, 16, (245, 245, 247), a=a)
        p.text(cx + 22, y + 204, nm, 15, INK2, a=a, bg=(245, 245, 247))
        p.text(cx + 20, y + 236, (f"{v:.1f}".replace(".", ",") if u == "°" else f"{v:.0f}") + u, 38, INK, "sb", a=a, bg=(245, 245, 247))


@scene(16, "Langkah 7")
def s_usb(p, t):
    judul(p, t, "Langkah 7: tampilkan di dashboard lewat USB")
    p.rr(80, 160, 560, 220, 22, (29, 29, 31))
    cmds = ["cd backend-api", "python -m venv .venv", ".venv/Scripts/pip install -r requirements.txt",
            "SERIAL_PORT=COM5 .venv/Scripts/python -m uvicorn app:app --host 0.0.0.0 --port 8000"]
    y = 186
    for i, c in enumerate(cmds):
        k = clamp((t - 0.6 - i * 1.4) / 1.0)
        if k <= 0:
            break
        for ln in p.wrap("$ " + c[:int(len(c) * k)], 16, 520, "m"):
            p.text(100, y, ln, 16, (245, 245, 247), "m", bg=(29, 29, 31))
            y += 26
    p.para(80, 400, "Nomor port (COM5) dilihat di Device Manager → Ports. Tutup dulu Monitor PlatformIO, karena satu port hanya bisa dipakai satu program.",
           18, 560, INK2, a=prog(t, 5, 0.6))
    p.para(80, 500, "Lalu buka http://localhost:8000 di browser.", 22, 560, BLUE, "sb", a=prog(t, 6.5, 0.6))
    k = clamp((t - 8) / 6)
    st = "Aman" if k < 0.4 else "Waspada" if k < 0.75 else "Bahaya"
    dashboard_mock(p, 690, 160, 510, st, 25 + 67 * k, 70 * k, 6.4 * clamp((k - 0.45) * 2), prog(t, 7.2, 0.6))
    kartu_cek(p, 690, 545, 510, "Tertulis “Menerima data dari alat”, dan angkanya ikut berubah saat sensor dibasahi.", prog(t, 12, 0.6))


@scene(18, "Langkah 8")
def s_wifi(p, t):
    judul(p, t, "Langkah 8: kirim data lewat WiFi", "Alat tidak perlu menempel ke laptop")
    nodes = [(120, "ESP32", "di lereng", (230, 241, 251)), (520, "Router / hotspot", "WiFi 2,4 GHz", (245, 245, 247)),
             (920, "Laptop", "192.168.1.10:8000", (245, 245, 247))]
    for i, (x, a1, b1, f) in enumerate(nodes):
        a = prog(t, 0.5 + i * 0.5, 0.5)
        p.rr(x, 200, 240, 110, 20, f, HAIR, 1.5, a)
        p.text(x + 120, 240, a1, 24, INK, "sb", "mm", a, bg=f)
        p.text(x + 120, 278, b1, 17, INK2, anchor="mm", a=a, bg=f)
    for x0, x1 in ((360, 520), (760, 920)):
        p.line([(x0, 255), (x1, 255)], HAIR, 3)
    if t > 2:
        for i in range(4):
            k = ((t - 2) * 0.35 + i / 4) % 1
            x = 360 + (920 - 360) * k
            if not (760 > x > 520):
                p.circle(x, 255, 7, BLUE)
    p.rr(80, 350, 640, 250, 22, (29, 29, 31), a=prog(t, 3, 0.6))
    code = ["// firmware/include/secrets.h", '#define WIFI_SSID  "nama WiFi kamu"', '#define WIFI_PASS  "kata sandi WiFi"',
            '#define SERVER_URL "http://192.168.1.10:8000/api/telemetry"', "", "// config.h:  #define KIRIM_WIFI 1"]
    for i, c in enumerate(code):
        p.text(104, 376 + i * 34, c, 16, (161, 161, 166) if c.startswith("//") else (245, 245, 247), "m",
               a=prog(t, 3.5 + i * 0.8, 0.5), bg=(29, 29, 31))
    p.rr(760, 350, 440, 250, 22, CARD, a=prog(t, 8, 0.6))
    tips = ["IP laptop: jalankan ipconfig, lihat IPv4 Address", "ESP32 tidak bisa WiFi 5 GHz. Hotspot HP bisa dipakai",
            "Saat Windows bertanya firewall, pilih Allow access", "secrets.h tidak ikut ter-push ke GitHub"]
    for i, s in enumerate(tips):
        a = prog(t, 8.5 + i * 1.2, 0.5)
        p.circle(790, 386 + i * 52, 6, BLUE, a=a)
        p.para(808, 374 + i * 52, s, 17, 370, INK, a=a, bg=CARD)
    kartu_cek(p, 80, 620, 1120, "Monitor menampilkan event wifi, dan dashboard tetap menerima data setelah USB dicabut.", prog(t, 14.5, 0.6))


@scene(13, "Langkah 9")
def s_telegram(p, t):
    judul(p, t, "Langkah 9: peringatan ke Telegram", "Opsional")
    steps = ["Buka @BotFather, kirim /newbot, simpan token-nya", "Kirim pesan apa saja ke bot barumu",
             "Ambil chat ID dari api.telegram.org/bot<TOKEN>/getUpdates",
             "Jalankan backend dengan TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID"]
    for i, s in enumerate(steps):
        a = prog(t, 0.6 + i * 1.3, 0.5)
        p.rr(80, 200 + i * 88, 640, 72, 18, CARD, a=a)
        p.circle(122, 236 + i * 88, 18, BLUE, a=a)
        p.text(122, 236 + i * 88, str(i + 1), 18, CARD, "sb", "mm", a, bg=BLUE)
        p.para(156, 214 + i * 88, s, 18, 540, INK, a=a, bg=CARD)
    # ponsel
    p.rr(850, 170, 300, 480, 40, (29, 29, 31))
    p.rr(866, 186, 268, 448, 28, (223, 231, 238))
    p.text(1000, 216, "SIARENG Bot", 16, INK, "sb", "mm", bg=(223, 231, 238))
    msgs = [(6.5, "SIARENG: waspada\nTanah 84% · hujan 62%\nKemiringan bergeser 2,6°", (255, 255, 255)),
            (9.0, "SIARENG: BAHAYA\nTanah 91% · geser 5,8°\nJauhi area lereng.", (255, 235, 238))]
    y = 250
    for st, m, f in msgs:
        a = prog(t, st, 0.5)
        if a <= 0:
            continue
        lines = m.split("\n")
        h = 22 + len(lines) * 24
        p.rr(880, y + 12 * (1 - a), 240, h, 16, f, a=a, )
        for j, ln in enumerate(lines):
            p.text(894, y + 14 + j * 24 + 12 * (1 - a), ln.replace("⚠ ", ""), 15, RED if "BAHAYA" in ln else INK,
                   "sb" if j == 0 else "r", a=a, bg=f)
        y += h + 14


@scene(14, "Selesai")
def s_penutup(p, t):
    p.text(80, 110, "Selesai di meja. Berikutnya: lapangan.", 44, INK, "sb", a=prog(t, 0, 0.6))
    p.para(82, 180, "Pindah ke PCB, catu daya panel surya, box tahan air, dan pemasangan di lereng ada di panduan-perakitan.md.",
           22, 620, INK2, a=prog(t, 0.6, 0.6))
    p.rr(700, 150, 500, 380, 28, CARD, a=prog(t, 0.4, 0.6))
    k = clamp((t - 1) / 6)
    lereng(p, 735, 200, 1.45, t, 0.2 + 0.75 * k, k, 15 * clamp(k * 1.6 - 0.6), GRN if k < 0.4 else YEL if k < 0.8 else RED,
           a=prog(t, 0.6, 0.6))
    rows = [("Panduan PDF", "docs/Panduan_SIARENG.pdf"), ("Kode lengkap", "github.com/YusufArrayyan/SIARENG"),
            ("Kalau ada masalah", "tabel “Kalau ada masalah” di PDF")]
    for i, (a1, b1) in enumerate(rows):
        a = prog(t, 1.5 + i * 0.6, 0.5)
        p.text(82, 300 + i * 60, a1, 18, INK2, a=a)
        p.text(82, 324 + i * 60, b1, 22, BLUE, "sb", a=a)
    p.rr(80, 560, 1120, 90, 18, (255, 244, 229), a=prog(t, 4, 0.6))
    p.para(104, 578, "SIARENG adalah alat pembelajaran. Ambang statusnya masih nilai awal untuk uji dan alat ini bukan sistem peringatan dini resmi. Untuk keadaan darurat, ikuti arahan BPBD setempat.",
           18, 1070, INK, a=prog(t, 4, 0.6), bg=(255, 244, 229))


# ------------------------------------------------------------------ render
TOTAL = sum(d for d, _c, _f in SCENES)


def frame(T):
    acc = 0
    for i, (d, chip, fn) in enumerate(SCENES):
        if T < acc + d or i == len(SCENES) - 1:
            t = T - acc
            break
        acc += d
    img = Image.new("RGB", (W * S, H * S), BG)
    p = Pen(img)
    fn(p, t)
    # kerangka: merek, chip langkah, progres
    p.text(80, 26, "SIARENG · Panduan perakitan", 15, INK2, "sb")
    if chip:
        cw = p.tw(chip, 15, "sb") + 32
        p.rr(1200 - cw, 18, cw, 30, 15, CARD, HAIR, 1)
        p.text(1200 - cw / 2, 33, chip, 15, INK, "sb", "mm", bg=CARD)
    p.rr(0, H - 6, W, 6, 0, (225, 225, 230))
    p.rr(0, H - 6, W * T / TOTAL, 6, 0, BLUE)
    # transisi: pudar di awal dan akhir adegan
    masuk = clamp(t / 0.35) if i > 0 else 1.0
    keluar = clamp((d - t) / 0.35) if i < len(SCENES) - 1 else 1.0
    fade = min(masuk, keluar)
    img = img.resize((OW, OH), Image.Resampling.LANCZOS)
    if fade < 1:
        img = Image.blend(Image.new("RGB", (OW, OH), BG), img, fade)
    return img


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return shutil.which("ffmpeg")


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--cek":
        for s in sys.argv[2:]:
            fn = HERE / f"cek_{s}.png"
            frame(float(s)).save(fn)
            print(fn)
        return
    exe = ffmpeg_exe()
    if not exe:
        sys.exit("ffmpeg tidak ditemukan. Jalankan: pip install imageio-ffmpeg")
    n = int(TOTAL * FPS)
    print(f"{len(SCENES)} adegan, {TOTAL:.0f} detik, {n} bingkai")
    proc = subprocess.Popen([exe, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT)], stdin=subprocess.PIPE)
    for i in range(n):
        proc.stdin.write(frame(i / FPS).tobytes())
        if i % (FPS * 10) == 0:
            print(f"  {i / FPS:.0f}/{TOTAL:.0f} detik", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"Video dibuat: {OUT}")


if __name__ == "__main__":
    main()
