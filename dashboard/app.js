"use strict";
/* SIARENG dashboard
 * Sumber data:
 *  - live : WebSocket ke backend-api (ws://host/ws), data asli dari ESP32.
 *  - demo : simulator di browser, memakai logika status yang sama dengan firmware
 *           (firmware/include/landslide_logic.h).
 * Buka dengan ?demo untuk memaksa mode demo walaupun backend berjalan.
 */

// Ambang sama dengan struct Ambang di landslide_logic.h
const AMBANG = { soilWaspada: 60, soilJenuh: 80, rainWaspada: 40, tiltWaspada: 2, tiltBahaya: 5, naikMs: 2000, turunMs: 6000 };
const SIMPAN_MS = 24 * 60 * 60 * 1000;  // riwayat yang disimpan di browser
const BASI_MS = 15 * 1000;              // tanpa data selama ini = perangkat dianggap diam
const LEVEL = { aman: 0, waspada: 1, bahaya: 2 };
const NAMA = ["aman", "waspada", "bahaya"];
const LABEL = { aman: "Aman", waspada: "Waspada", bahaya: "Bahaya", diam: "Tidak ada data" };
const IKON = { aman: "#i-ok", waspada: "#i-warn", bahaya: "#i-alarm", diam: "#i-off" };

const fmt1 = new Intl.NumberFormat("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const fmt0 = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 });
const fmtJam = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const fmtJamPendek = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit" });

const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

// ------------------------------------------------------------------ state
const state = {
  mode: "demo",                 // demo | live
  conn: "demo",                 // demo | connecting | live | stale | offline
  samples: [],                  // {t, soil, rain, tilt, status}
  events: [],                   // {t, level, text}
  status: "aman",
  statusSince: Date.now(),
  last: null,                   // telemetri terakhir (objek dari perangkat)
  lastAt: 0,
  dangerMsToday: 0,
  dangerDay: new Date().toDateString(),
  series: "soil",
  rangeMin: 10,
  hoverX: null,
  sound: false,
};

// ------------------------------------------------------------------ logika status (salinan firmware)
function kandidat(p) {
  const basah = p.soil >= AMBANG.soilWaspada, jenuh = p.soil >= AMBANG.soilJenuh;
  const hujan = p.rain >= AMBANG.rainWaspada;
  const bergeser = p.tilt >= AMBANG.tiltWaspada, miring = p.tilt >= AMBANG.tiltBahaya;
  if (jenuh && miring) return 2;
  if (jenuh || bergeser || (basah && hujan)) return 1;
  return 0;
}

class PenilaiStatus {
  constructor() { this.s = 0; this.naik = false; this.turun = false; this.t0 = 0; this.minNaik = 0; this.maksTurun = 0; }
  perbarui(k, now) {
    if (k === this.s) { this.naik = this.turun = false; return false; }
    if (k > this.s) {
      this.turun = false;
      if (!this.naik) { this.naik = true; this.t0 = now; this.minNaik = k; } else if (k < this.minNaik) this.minNaik = k;
      if (now - this.t0 >= AMBANG.naikMs) { this.s = this.minNaik; this.naik = false; return true; }
    } else {
      this.naik = false;
      if (!this.turun) { this.turun = true; this.t0 = now; this.maksTurun = k; } else if (k > this.maksTurun) this.maksTurun = k;
      if (now - this.t0 >= AMBANG.turunMs) { this.s = this.maksTurun; this.turun = false; return true; }
    }
    return false;
  }
}

// Kalimat alasan status, diturunkan dari pembacaan
function alasan(status, p) {
  const tilt = fmt1.format(p.tilt);
  if (status === "bahaya") return `Tanah jenuh air (${fmt0.format(p.soil)}%) dan lereng bergeser ${tilt}°. Jauhi area lereng.`;
  if (status === "waspada") {
    if (p.soil >= AMBANG.soilJenuh) return `Tanah jenuh air (${fmt0.format(p.soil)}%). Pantau pergeseran lereng.`;
    if (p.tilt >= AMBANG.tiltWaspada) return `Lereng bergeser ${tilt}° dari posisi awal.`;
    if (p.soil >= AMBANG.soilWaspada && p.rain >= AMBANG.rainWaspada) return `Tanah basah (${fmt0.format(p.soil)}%) saat hujan deras.`;
    return "Kondisi sedang kembali normal.";
  }
  return "Tanah dan kemiringan masih dalam batas normal.";
}

function levelMetrik(k, v) {
  if (k === "soil") return v >= AMBANG.soilJenuh ? "bahaya" : v >= AMBANG.soilWaspada ? "waspada" : "aman";
  if (k === "rain") return v >= AMBANG.rainWaspada ? "waspada" : "aman";
  return v >= AMBANG.tiltBahaya ? "bahaya" : v >= AMBANG.tiltWaspada ? "waspada" : "aman";
}
function labelMetrik(k, v) {
  if (k === "soil") return v >= AMBANG.soilJenuh ? "Jenuh" : v >= AMBANG.soilWaspada ? "Basah" : "Kering";
  if (k === "rain") return v >= AMBANG.rainWaspada ? "Deras" : v >= 5 ? "Ringan" : "Tidak hujan";
  return v >= AMBANG.tiltBahaya ? "Miring" : v >= AMBANG.tiltWaspada ? "Bergeser" : "Stabil";
}

// Status yang ditampilkan: "diam" bila data sudah basi, supaya layar tidak menampilkan "Aman" palsu.
function statusTampil(now = Date.now()) {
  if (state.mode === "live" && (!state.lastAt || now - state.lastAt > BASI_MS)) return "diam";
  return state.status;
}

// ------------------------------------------------------------------ ingest
const keSampel = (d, t) => ({ t, soil: +d.soil_pct || 0, rain: +d.rain_pct || 0, tilt: +d.tilt_delta_deg || 0, status: d.status || "aman" });

function pangkas(now) {
  const batas = now - SIMPAN_MS;
  while (state.samples.length && state.samples[0].t < batas) state.samples.shift();
}

function ingestTelemetry(d, t = Date.now()) {
  const p = keSampel(d, t);
  const today = new Date(t).toDateString();
  if (today !== state.dangerDay) { state.dangerDay = today; state.dangerMsToday = 0; }
  if (state.lastAt && state.status === "bahaya") state.dangerMsToday += Math.min(t - state.lastAt, BASI_MS);

  state.samples.push(p);
  pangkas(t);
  if (p.status !== state.status) setStatus(p.status, t);
  state.last = d;
  state.lastAt = t;
  if (state.mode === "live") setConn("live");
  scheduleRender();
}

// Ubah event firmware menjadi baris daftar kejadian
function teksEvent(d) {
  switch (d.event) {
    case "status_change": {
      const ke = d.to || "aman";
      return { level: ke, text: `Status ${d.from ? d.from + " → " : ""}${ke}`, ke };
    }
    case "kalibrasi_ulang": return { level: "info", text: "Kalibrasi ulang kemiringan. Posisi sekarang menjadi patokan baru." };
    case "baseline_siap": return { level: "info", text: "Patokan kemiringan siap. Pemantauan dimulai." };
    case "boot": return { level: "info", text: "Perangkat menyala." };
    case "error": return { level: "bahaya", text: d.msg || "Perangkat melaporkan galat." };
    default: return null;
  }
}

function ingestEvent(d, t = Date.now()) {
  const e = teksEvent(d);
  if (!e) return;
  addEvent(t, e.level, e.text);
  if (e.ke) setStatus(e.ke, t);
  scheduleRender();
}

function addEvent(t, level, text) {
  state.events.unshift({ t, level, text });
  if (state.events.length > 200) state.events.pop();
}

// Riwayat dari server: isi grafik dan daftar kejadian tanpa memicu alarm untuk kejadian lama.
function muatRiwayat(telemetry, events) {
  const baru = telemetry.map((h) => keSampel(h.data, h.ts));
  const tAkhir = baru.length ? baru.at(-1).t : 0;
  state.samples = baru.concat(state.samples.filter((s) => s.t > tAkhir));
  if (events) {
    state.events = [];
    for (const e of events) {                       // server mengirim terbaru dulu
      const x = teksEvent(e.data);
      if (x) state.events.push({ t: e.ts, level: x.level, text: x.text });
    }
  }
  const h = telemetry.at(-1);
  if (h && h.ts >= state.lastAt) {
    state.last = h.data; state.lastAt = h.ts;
    const s = h.data.status;
    if (s in LEVEL && s !== state.status) {
      state.status = s;
      const ubah = events?.find((e) => e.data.event === "status_change" && e.data.to === s);
      state.statusSince = ubah ? ubah.ts : h.ts;
    }
  }
  scheduleRender();
}

function setStatus(s, t) {
  if (!(s in LEVEL) || s === state.status) return;
  state.status = s;
  state.statusSince = t;
  if (s === "bahaya") notifyDanger();
}

// ------------------------------------------------------------------ alarm
let audioCtx = null, alarmTimer = null;
function beep() {
  if (!audioCtx) return;
  const o = audioCtx.createOscillator(), g = audioCtx.createGain();
  o.frequency.value = 2000; o.type = "square";
  g.gain.setValueAtTime(0.06, audioCtx.currentTime);
  g.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.22);
  o.connect(g).connect(audioCtx.destination); o.start(); o.stop(audioCtx.currentTime + 0.25);
}
function startAlarm() { if (!state.sound || alarmTimer) return; beep(); alarmTimer = setInterval(beep, 500); }
function stopAlarm() { clearInterval(alarmTimer); alarmTimer = null; }

function notifyDanger() {
  startAlarm();
  if ("Notification" in window && Notification.permission === "granted") {
    const p = state.samples.at(-1);
    new Notification("SIARENG: status BAHAYA", { body: p ? alasan("bahaya", p) : "Periksa lereng sekarang.", tag: "siareng-bahaya", requireInteraction: true });
  }
}

// ------------------------------------------------------------------ render
let renderQueued = false;
function scheduleRender() {
  if (renderQueued) return;
  renderQueued = true;
  // requestAnimationFrame berhenti saat tab di latar belakang atau jendela tertutup jendela lain.
  // Timer cadangan memastikan judul tab, banner, dan alarm tetap diperbarui saat dashboard tidak dilihat.
  const raf = requestAnimationFrame(jalan);
  const timer = setTimeout(jalan, 250);
  function jalan() { cancelAnimationFrame(raf); clearTimeout(timer); if (renderQueued) render(); }
}

function render() {
  renderQueued = false;
  const now = Date.now();
  const p = state.samples.at(-1);
  const st = statusTampil(now);
  const diam = st === "diam";

  // hero
  $("#hero").dataset.status = st;
  $("#hero-status").textContent = LABEL[st];
  $("#hero-icon-use").setAttribute("href", IKON[st]);
  if (diam) {
    $("#hero-reason").textContent = state.lastAt
      ? `Alat berhenti mengirim data ${durasi(now - state.lastAt)} lalu. Status lereng tidak diketahui. Periksa daya dan sambungan alat.`
      : "Menunggu data pertama dari alat.";
    $("#hero-since").textContent = state.lastAt ? `Status terakhir: ${LABEL[state.status].toLowerCase()}` : "Belum pernah tersambung";
    $("#hero-updated").textContent = state.lastAt ? `Data terakhir pukul ${fmtJam.format(state.lastAt)}` : "Belum ada data";
  } else {
    $("#hero-reason").textContent = p ? alasan(st, p) : "Menunggu data pertama dari alat.";
    $("#hero-since").textContent = `Sejak ${fmtJamPendek.format(state.statusSince)} (${durasi(now - state.statusSince)})`;
    $("#hero-updated").textContent = state.lastAt ? `Data terakhir ${durasi(now - state.lastAt)} lalu` : "Menunggu data";
  }
  $$(".ladder li").forEach((li) => li.classList.toggle("on", li.dataset.level === st));
  if (state.last?.device_id) $("#hero-place").textContent = `Lereng uji · ${state.last.device_id}`;
  document.body.classList.toggle("stale", diam);
  $("#setup").hidden = !(state.mode === "live" && !state.lastAt && state.conn !== "connecting");

  // banner, judul tab, alarm
  const bahaya = st === "bahaya";
  $("#alert-banner").hidden = !bahaya;
  if (bahaya && p) $("#alert-text").textContent = `Status bahaya. ${alasan("bahaya", p)}`;
  document.title = bahaya ? "BAHAYA · SIARENG" : st === "waspada" ? "Waspada · SIARENG" : diam ? "Tidak ada data · SIARENG" : "SIARENG · Pemantau Lereng";
  if (bahaya) startAlarm(); else stopAlarm();

  // metrik + ilustrasi
  if (p) {
    metric("soil", p.soil, p.soil, fmt0.format(p.soil));
    metric("rain", p.rain, p.rain, fmt0.format(p.rain));
    metric("tilt", p.tilt, Math.min(p.tilt * 10, 100), fmt1.format(p.tilt));
    $("#sc-pole").style.transform = `rotate(${Math.min(p.tilt * 3, 40).toFixed(1)}deg)`;
    $("#sc-wet").style.opacity = (Math.min(p.soil, 100) / 100 * 0.75).toFixed(2);
    const rain = $("#sc-rain");
    rain.style.opacity = diam ? 0 : Math.min(p.rain / 60, 1).toFixed(2);
    rain.classList.toggle("on", !diam && p.rain >= 5);
  }

  renderEvents();
  renderAnalytics(now);
  drawChart();
}

function metric(k, v, pct, text) {
  const card = $(`#m-${k}`);
  card.dataset.level = levelMetrik(k, v);
  card.querySelector(".num").textContent = text;
  card.querySelector(".chip").textContent = labelMetrik(k, v);
  card.querySelector(".meter-fill").style.width = `${Math.max(0, Math.min(100, pct))}%`;

  // sparkline: 60 pembacaan terakhir
  const pts = state.samples.slice(-60), maks = k === "tilt" ? 10 : 100;
  if (pts.length > 1) {
    card.querySelector("polyline").setAttribute("points",
      pts.map((s, i) => `${(i / (pts.length - 1) * 100).toFixed(1)},${(30 - Math.min(s[k], maks) / maks * 28).toFixed(1)}`).join(" "));
  }
}

let eventsKey = "";
function renderEvents() {
  const key = state.events.length + "|" + (state.events[0]?.t || 0);
  if (key === eventsKey) return;                    // jangan bangun ulang daftar bila tidak berubah
  eventsKey = key;
  const ul = $("#events");
  $("#events-empty").hidden = state.events.length > 0;
  ul.replaceChildren();
  const hariIni = new Date().toDateString();
  for (const e of state.events.slice(0, 50)) {
    const li = document.createElement("li");
    const waktu = document.createElement("span"); waktu.className = "ev-time";
    const tgl = new Date(e.t);
    waktu.textContent = tgl.toDateString() === hariIni ? fmtJamPendek.format(tgl) : `${tgl.getDate()}/${tgl.getMonth() + 1} ${fmtJamPendek.format(tgl)}`;
    const teks = document.createElement("span"); teks.className = "ev-text";
    const tag = document.createElement("span"); tag.className = `ev-tag ${e.level}`;
    tag.textContent = e.level === "info" ? "Info" : LABEL[e.level] || e.level;
    teks.append(tag, document.createTextNode(e.text));
    li.append(waktu, teks);
    ul.append(li);
  }
}

function renderAnalytics(now) {
  const s = state.samples;
  if (s.length > 1) {
    const ref = s.find((x) => x.t >= s.at(-1).t - 5 * 60 * 1000) || s[0];
    const d = s.at(-1).soil - ref.soil;
    $("#a-trend").textContent = Math.abs(d) < 0.05 ? "Stabil"
      : `${d > 0 ? "Naik" : "Turun"} ${fmt1.format(Math.abs(d))} poin dalam ${durasi(s.at(-1).t - ref.t)}`;

    const win = s.slice(-120, -3).map((x) => x.tilt);
    if (win.length >= 20) {
      const mean = win.reduce((a, b) => a + b, 0) / win.length;
      const sd = Math.max(0.05, Math.sqrt(win.reduce((a, b) => a + (b - mean) ** 2, 0) / win.length));
      const z = (s.at(-1).tilt - mean) / sd;
      $("#a-z").textContent = `${fmt1.format(z)} · ${Math.abs(z) >= 3 ? "lonjakan" : "normal"}`;
    } else {
      $("#a-z").textContent = "Mengumpulkan data";
    }
  }
  $("#a-danger").textContent = durasi(state.dangerMsToday);

  const d = state.last;
  $("#d-id").textContent = d?.device_id || "–";
  $("#d-seq").textContent = d?.seq != null ? `#${fmt0.format(d.seq)}` : "–";
  $("#d-uptime").textContent = d?.uptime_ms != null ? durasi(d.uptime_ms) : "–";
  $("#d-raw").textContent = d?.soil_raw != null ? `${d.soil_raw} / ${d.rain_raw}` : "–";
  const r = d?.rssi;
  $("#d-rssi").textContent = r ? `${r} dBm · ${r >= -60 ? "kuat" : r >= -75 ? "cukup" : "lemah"}` : d ? (d.mode === "sim" ? "Simulasi" : "Lewat USB") : "–";
}

function durasi(ms) {
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s} dtk`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} mnt`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} jam ${m % 60} mnt`;
  return `${Math.floor(h / 24)} hari ${h % 24} jam`;
}

// ------------------------------------------------------------------ grafik (canvas, tanpa pustaka)
const SERIES = {
  soil: { nama: "Kelembapan tanah", max: 100, unit: "%", marks: [[AMBANG.soilWaspada, "Basah", "warn"], [AMBANG.soilJenuh, "Jenuh", "danger"]], fmt: (v) => fmt0.format(v) },
  rain: { nama: "Intensitas hujan", max: 100, unit: "%", marks: [[AMBANG.rainWaspada, "Deras", "warn"]], fmt: (v) => fmt0.format(v) },
  tilt: { nama: "Pergeseran kemiringan", max: 10, unit: "°", marks: [[AMBANG.tiltWaspada, "Waspada", "warn"], [AMBANG.tiltBahaya, "Bahaya", "danger"]], fmt: (v) => fmt1.format(v) },
};
const PAD = { L: 44, R: 68, T: 34, B: 26 };

function cssVar(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }

function drawChart() {
  const cv = $("#chart"), box = cv.parentElement;
  const dpr = window.devicePixelRatio || 1, W = box.clientWidth, H = box.clientHeight;
  if (!W || !H) return;
  if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); }
  const c = cv.getContext("2d");
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  c.clearRect(0, 0, W, H);

  const cfg = SERIES[state.series], k = state.series;
  const col = { ink: cssVar("--ink"), ink2: cssVar("--ink-2"), hair: cssVar("--hairline"), primary: cssVar("--primary"), danger: cssVar("--danger"), warn: cssVar("--warn") };
  const pw = W - PAD.L - PAD.R, ph = H - PAD.T - PAD.B;
  const rangeMs = state.rangeMin * 60000, now = Date.now(), t0 = now - rangeMs;
  const x = (t) => PAD.L + ((t - t0) / rangeMs) * pw;
  const y = (v) => PAD.T + ph - (Math.min(v, cfg.max) / cfg.max) * ph;
  c.font = "12px " + cssVar("--font-text");

  // grid
  c.strokeStyle = col.hair; c.lineWidth = 1; c.fillStyle = col.ink2; c.textAlign = "right"; c.textBaseline = "middle";
  for (let i = 0; i <= 4; i++) {
    const v = (cfg.max / 4) * i, yy = Math.round(y(v)) + 0.5;
    c.globalAlpha = 0.6; c.beginPath(); c.moveTo(PAD.L, yy); c.lineTo(PAD.L + pw, yy); c.stroke(); c.globalAlpha = 1;
    c.fillText(cfg.fmt(v) + cfg.unit, PAD.L - 8, yy);
  }
  c.textBaseline = "top";
  const ticks = W < 520 ? 3 : 5;
  for (let i = 0; i <= ticks; i++) {
    const t = t0 + (rangeMs / ticks) * i;
    c.textAlign = i === 0 ? "left" : i === ticks ? "right" : "center";
    c.fillText(i === ticks ? "Sekarang" : fmtJamPendek.format(t), x(t), PAD.T + ph + 8);
  }

  // ambang
  c.setLineDash([5, 5]); c.textAlign = "left"; c.textBaseline = "middle";
  for (const [v, label, warna] of cfg.marks) {
    c.strokeStyle = col[warna]; c.globalAlpha = 0.8;
    c.beginPath(); c.moveTo(PAD.L, y(v)); c.lineTo(PAD.L + pw, y(v)); c.stroke();
    c.globalAlpha = 1; c.fillStyle = col[warna]; c.fillText(label, PAD.L + pw + 8, y(v));
  }
  c.setLineDash([]);

  const pts = state.samples.filter((p) => p.t >= t0);
  const tip = $("#tip");
  if (pts.length < 2) {
    c.fillStyle = col.ink2; c.textAlign = "center";
    c.fillText(state.mode === "live" ? "Belum ada data pada rentang ini" : "Mengumpulkan data", PAD.L + pw / 2, PAD.T + ph / 2);
    tip.hidden = true;
    return;
  }

  // garis; jeda lebih dari 30 detik (alat mati) digambar terputus
  const jeda = Math.max(30000, rangeMs / 120);
  c.beginPath();
  pts.forEach((p, i) => {
    if (i === 0 || p.t - pts[i - 1].t > jeda) c.moveTo(x(p.t), y(p[k])); else c.lineTo(x(p.t), y(p[k]));
  });
  c.strokeStyle = col.primary; c.lineWidth = 2; c.lineJoin = "round"; c.stroke();

  // area lembut di bawah garis
  c.beginPath(); c.moveTo(x(pts[0].t), y(0));
  for (const p of pts) c.lineTo(x(p.t), y(p[k]));
  c.lineTo(x(pts.at(-1).t), y(0)); c.closePath();
  c.globalAlpha = 0.07; c.fillStyle = col.primary; c.fill(); c.globalAlpha = 1;

  // pita di dasar grafik: kapan status waspada / bahaya (bentuk + posisi, bukan hanya warna garis)
  for (let i = 1; i < pts.length; i++) {
    const s = pts[i].status;
    if (s === "aman" || pts[i].t - pts[i - 1].t > jeda) continue;
    c.fillStyle = s === "bahaya" ? col.danger : col.warn;
    c.fillRect(x(pts[i - 1].t), PAD.T + ph - 4, Math.max(1, x(pts[i].t) - x(pts[i - 1].t)), 4);
  }

  // nilai terkini
  const last = pts.at(-1);
  c.fillStyle = col.primary; c.beginPath(); c.arc(x(last.t), y(last[k]), 4.5, 0, Math.PI * 2); c.fill();
  cv.setAttribute("aria-label", `Grafik ${cfg.nama.toLowerCase()}, nilai sekarang ${cfg.fmt(last[k])}${cfg.unit}`);

  // kursor
  if (state.hoverX == null || state.hoverX < PAD.L || state.hoverX > PAD.L + pw) { tip.hidden = true; return; }
  const th = t0 + ((state.hoverX - PAD.L) / pw) * rangeMs;
  let lo = 0, hi = pts.length - 1;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (pts[mid].t < th) lo = mid + 1; else hi = mid; }
  const near = lo > 0 && th - pts[lo - 1].t < pts[lo].t - th ? pts[lo - 1] : pts[lo];
  const hx = x(near.t), hy = y(near[k]);
  c.strokeStyle = col.ink2; c.lineWidth = 1; c.globalAlpha = 0.6;
  c.beginPath(); c.moveTo(Math.round(hx) + 0.5, PAD.T); c.lineTo(Math.round(hx) + 0.5, PAD.T + ph); c.stroke(); c.globalAlpha = 1;
  c.fillStyle = cssVar("--card"); c.strokeStyle = col.primary; c.lineWidth = 2;
  c.beginPath(); c.arc(hx, hy, 5, 0, Math.PI * 2); c.fill(); c.stroke();
  tip.hidden = false;
  tip.replaceChildren();
  const b = document.createElement("b"); b.textContent = `${cfg.fmt(near[k])}${cfg.unit}`;
  tip.append(b, ` · ${fmtJam.format(near.t)} · ${LABEL[near.status] || near.status}`);
  tip.style.left = `${Math.max(90, Math.min(W - 90, hx))}px`;
}

const chartBox = $("#chart").parentElement;
chartBox.addEventListener("pointermove", (e) => { state.hoverX = e.clientX - chartBox.getBoundingClientRect().left; drawChart(); });
chartBox.addEventListener("pointerleave", () => { state.hoverX = null; drawChart(); });

// ------------------------------------------------------------------ koneksi
function setConn(c) {
  if (state.conn === c) return;
  state.conn = c;
  $("#conn").dataset.state = c;
  $("#conn-text").textContent = {
    demo: "Mode demo: data simulasi",
    connecting: "Menyambung ke server…",
    live: "Menerima data dari alat",
    stale: "Alat tidak mengirim data",
    offline: "Server terputus, mencoba lagi…",
  }[c];
}

function ambilRiwayat() {
  return fetch(`/api/history?menit=${state.rangeMin}`, { cache: "no-store" })
    .then((r) => r.json())
    .then((j) => muatRiwayat(j.telemetry, j.events))
    .catch(() => {});
}

// Mode live: WebSocket ke backend-api
function startLive() {
  state.mode = "live";
  $("#demo").hidden = true;
  setConn("connecting");
  const url = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws";
  let retry = 1000;
  const connect = () => {
    const ws = new WebSocket(url);
    ws.onopen = () => { retry = 1000; };
    ws.onmessage = (m) => {
      const msg = JSON.parse(m.data);
      if (msg.type === "hello") {
        muatRiwayat(msg.history || [], msg.events || []);
        setConn(state.lastAt && Date.now() - state.lastAt < BASI_MS ? "live" : "stale");
        if (state.rangeMin !== 10) ambilRiwayat();
      } else if (msg.type === "telemetry") ingestTelemetry(msg.data, msg.ts);
      else if (msg.type === "event") ingestEvent(msg.data, msg.ts);
    };
    ws.onclose = () => { setConn("offline"); setTimeout(connect, retry); retry = Math.min(retry * 2, 15000); };
  };
  connect();
}

// Mode demo: simulator dengan logika firmware
function startDemo() {
  state.mode = "demo";
  setConn("demo");
  const input = { soil: 20, rain: 0, tilt: 0 };
  const f = { soil: 20, rain: 0, tilt: 0 };          // filter EMA (ALFA 0,3 seperti firmware)
  let baseline = 0, penilai = new PenilaiStatus(), seq = 0, tKirim = 0;
  const mulai = Date.now();

  const bind = (k, fmt) => {
    const s = $(`#s-${k}`), o = $(`#o-${k}`);
    const set = () => { input[k] = +s.value; o.textContent = fmt(+s.value); };
    s.addEventListener("input", set); set();
    return (v) => { s.value = v; set(); };
  };
  const setSoil = bind("soil", (v) => fmt0.format(v) + "%");
  const setRain = bind("rain", (v) => fmt0.format(v) + "%");
  const setTilt = bind("tilt", (v) => fmt1.format(v) + "°");

  const preset = { aman: [20, 0, 0], hujan: [68, 75, 0.4], bahaya: [92, 85, 6.5] };
  $$("[data-preset]").forEach((b) => b.addEventListener("click", () => {
    const [a, b2, c] = preset[b.dataset.preset]; setSoil(a); setRain(b2); setTilt(c);
  }));
  $("#btn-calib").addEventListener("click", () => {
    baseline = input.tilt; penilai = new PenilaiStatus();
    ingestEvent({ event: "kalibrasi_ulang" });
    setStatus("aman", Date.now());
  });

  ingestEvent({ event: "boot" }, mulai);
  ingestEvent({ event: "baseline_siap" }, mulai);

  setInterval(() => {
    const now = Date.now();
    for (const k of ["soil", "rain", "tilt"]) f[k] = 0.3 * input[k] + 0.7 * f[k];
    const p = { soil: f.soil, rain: f.rain, tilt: Math.max(0, f.tilt - baseline) };
    const sebelum = penilai.s;
    const berubah = penilai.perbarui(kandidat(p), now);
    if (berubah) ingestEvent({ event: "status_change", from: NAMA[sebelum], to: NAMA[penilai.s] }, now);
    if (berubah || now - tKirim >= [2000, 1000, 500][penilai.s]) {
      tKirim = now;
      ingestTelemetry({
        device_id: "esp32-longsor-lereng01", seq: ++seq, uptime_ms: now - mulai, mode: "sim",
        status: NAMA[penilai.s], soil_pct: +p.soil.toFixed(1), rain_pct: +p.rain.toFixed(1),
        tilt_delta_deg: +p.tilt.toFixed(1), alert: penilai.s === 2,
        soil_raw: Math.round(3200 - p.soil * 18), rain_raw: Math.round(4095 - p.rain * 28.95),
      }, now);
    }
  }, 200);
}

// ------------------------------------------------------------------ kontrol UI
function segmented(sel, attr, onPick) {
  $$(`${sel} button`).forEach((b) => b.addEventListener("click", () => {
    $$(`${sel} button`).forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    onPick(b.dataset[attr]);
  }));
}
segmented("#seg-series", "series", (v) => { state.series = v; drawChart(); });
segmented("#seg-range", "range", (v) => {
  state.rangeMin = +v;
  if (state.mode === "live") ambilRiwayat(); else drawChart();
});

$("#btn-csv").addEventListener("click", () => {
  if (state.mode === "live") { location.href = `/api/export.csv?menit=${state.rangeMin}`; return; }
  const baris = ["waktu,status,soil_pct,rain_pct,tilt_delta_deg",
    ...state.samples.map((s) => `${new Date(s.t).toISOString()},${s.status},${s.soil},${s.rain},${s.tilt}`)];
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([baris.join("\n")], { type: "text/csv" }));
  a.download = "siareng-demo.csv";
  a.click();
  URL.revokeObjectURL(a.href);
});

$("#btn-sound").addEventListener("click", (e) => {
  state.sound = !state.sound;
  if (state.sound && !audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  e.currentTarget.setAttribute("aria-pressed", String(state.sound));
  e.currentTarget.textContent = `Bunyi alarm: ${state.sound ? "nyala" : "mati"}`;
  if (state.sound) { beep(); if (statusTampil() === "bahaya") startAlarm(); } else stopAlarm();
});

const btnNotify = $("#btn-notify");
function syncNotifyButton() {
  if (!("Notification" in window)) { btnNotify.hidden = true; return; }
  if (Notification.permission === "granted") { btnNotify.textContent = "Notifikasi aktif"; btnNotify.disabled = true; }
  else if (Notification.permission === "denied") { btnNotify.textContent = "Notifikasi diblokir browser"; btnNotify.disabled = true; }
}
btnNotify.addEventListener("click", () => Notification.requestPermission().then(syncNotifyButton));
syncNotifyButton();

window.addEventListener("resize", drawChart);

// Penanda data basi + penyegaran label waktu
setInterval(() => {
  if (state.mode === "live" && state.conn !== "offline" && state.conn !== "connecting") {
    setConn(state.lastAt && Date.now() - state.lastAt < BASI_MS ? "live" : "stale");
  }
  scheduleRender();
}, 1000);

// ------------------------------------------------------------------ mulai
const paksaDemo = new URLSearchParams(location.search).has("demo");
if (location.protocol.startsWith("http") && !paksaDemo) {
  // Coba backend dulu; kalau /api/health tidak ada, pakai mode demo.
  fetch("/api/health", { cache: "no-store" })
    .then((r) => (r.ok ? startLive() : startDemo()))
    .catch(startDemo);
} else {
  startDemo();
}
render();
