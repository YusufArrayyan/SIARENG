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
const RIWAYAT_MS = 10 * 60 * 1000;
const BASI_MS = 10 * 1000;              // tanpa data selama ini = perangkat dianggap diam
const LEVEL = { aman: 0, waspada: 1, bahaya: 2 };
const NAMA = ["aman", "waspada", "bahaya"];
const LABEL = { aman: "Aman", waspada: "Waspada", bahaya: "Bahaya" };

const fmt1 = new Intl.NumberFormat("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const fmt0 = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 });
const fmtJam = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const fmtJamPendek = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit" });

const $ = (s) => document.querySelector(s);

// ------------------------------------------------------------------ state
const state = {
  mode: "demo",                 // demo | live
  conn: "demo",                 // demo | connecting | live | stale | offline
  samples: [],                  // {t, soil, rain, tilt, status}
  events: [],                   // {t, kind, text, level}
  status: "aman",
  statusSince: Date.now(),
  last: null,                   // telemetri terakhir (objek dari perangkat)
  lastAt: 0,
  dangerMsToday: 0,
  dangerDay: new Date().toDateString(),
  series: "soil",
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

// ------------------------------------------------------------------ ingest
function ingestTelemetry(d, t = Date.now()) {
  const p = { t, soil: +d.soil_pct || 0, rain: +d.rain_pct || 0, tilt: +d.tilt_delta_deg || 0, status: d.status || "aman" };
  // akumulasi waktu bahaya hari ini
  const today = new Date(t).toDateString();
  if (today !== state.dangerDay) { state.dangerDay = today; state.dangerMsToday = 0; }
  if (state.lastAt && state.status === "bahaya") state.dangerMsToday += Math.min(t - state.lastAt, BASI_MS);

  state.samples.push(p);
  const batas = t - RIWAYAT_MS;
  while (state.samples.length && state.samples[0].t < batas) state.samples.shift();

  if (p.status !== state.status) setStatus(p.status, t, false);
  state.last = d;
  state.lastAt = t;
  if (state.mode === "live") setConn("live");
  scheduleRender();
}

function ingestEvent(d, t = Date.now()) {
  if (d.event === "status_change") {
    const ke = d.to || "aman";
    addEvent(t, ke, `Status ${d.from ? LABEL[d.from]?.toLowerCase() + " → " : ""}${LABEL[ke]?.toLowerCase() || ke}`);
    setStatus(ke, t, true);
  } else if (d.event === "kalibrasi_ulang") {
    addEvent(t, "info", "Kalibrasi ulang kemiringan. Posisi sekarang menjadi patokan baru.");
  } else if (d.event === "baseline_siap") {
    addEvent(t, "info", "Patokan kemiringan siap. Pemantauan dimulai.");
  } else if (d.event === "boot") {
    addEvent(t, "info", "Perangkat menyala.");
  } else if (d.event === "error") {
    addEvent(t, "bahaya", d.msg || "Perangkat melaporkan galat.");
  }
  scheduleRender();
}

function addEvent(t, level, text) {
  state.events.unshift({ t, level, text });
  if (state.events.length > 100) state.events.pop();
}

function setStatus(s, t, fromEvent) {
  if (!(s in LEVEL) || s === state.status) return;
  // Catatan kejadian hanya dibuat dari event status_change, supaya tidak dobel
  // bila telemetri dengan status baru tiba lebih dulu daripada event-nya.
  const naik = LEVEL[s] > LEVEL[state.status];
  state.status = s;
  state.statusSince = t;
  if (s === "bahaya") notifyDanger();
  if (!naik && s !== "bahaya") stopAlarm();
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
function scheduleRender() { if (!renderQueued) { renderQueued = true; requestAnimationFrame(render); } }

function render() {
  renderQueued = false;
  const now = Date.now();
  const p = state.samples.at(-1);

  // hero
  const hero = $("#hero");
  hero.dataset.status = state.status;
  $("#hero-status").textContent = LABEL[state.status];
  $("#hero-icon-use").setAttribute("href", state.status === "aman" ? "#i-ok" : state.status === "waspada" ? "#i-warn" : "#i-alarm");
  $("#hero-reason").textContent = p ? alasan(state.status, p) : "Menunggu data pertama dari perangkat.";
  $("#hero-since").textContent = `Sejak ${fmtJamPendek.format(state.statusSince)} (${durasi(now - state.statusSince)})`;
  $("#hero-updated").textContent = state.lastAt ? `Data terakhir ${durasi(now - state.lastAt)} lalu` : "Menunggu data";
  document.querySelectorAll(".ladder li").forEach((li) => li.classList.toggle("on", li.dataset.level === state.status));
  if (state.last?.device_id) $("#hero-place").textContent = `Lereng uji · ${state.last.device_id}`;

  // banner + judul tab
  const bahaya = state.status === "bahaya";
  $("#alert-banner").hidden = !bahaya;
  if (bahaya && p) $("#alert-text").textContent = `Status bahaya. ${alasan("bahaya", p)}`;
  document.title = bahaya ? "BAHAYA · SIARENG" : state.status === "waspada" ? "Waspada · SIARENG" : "SIARENG · Pemantau Lereng";
  if (bahaya) startAlarm(); else stopAlarm();

  // metrik
  if (p) {
    metric("soil", p.soil, p.soil, fmt0.format(p.soil));
    metric("rain", p.rain, p.rain, fmt0.format(p.rain));
    metric("tilt", p.tilt, Math.min(p.tilt * 10, 100), fmt1.format(p.tilt));
  }

  renderEvents();
  renderAnalytics(now);
  drawChart();
}

function metric(k, v, pct, text) {
  const card = $(`#m-${k}`);
  card.dataset.level = levelMetrik(k, v);
  card.querySelector(".num").textContent = text;
  card.querySelector(".meter-fill").style.width = `${Math.max(0, Math.min(100, pct))}%`;
}

function renderEvents() {
  const ul = $("#events");
  $("#events-empty").hidden = state.events.length > 0;
  ul.innerHTML = "";
  for (const e of state.events.slice(0, 40)) {
    const li = document.createElement("li");
    const tag = e.level === "info" ? "Info" : LABEL[e.level] || e.level;
    li.innerHTML = `<span class="ev-time">${fmtJamPendek.format(e.t)}</span><span class="ev-text"><span class="ev-tag ${e.level}">${tag}</span></span>`;
    li.querySelector(".ev-text").append(document.createTextNode(e.text));
    ul.append(li);
  }
}

function renderAnalytics(now) {
  const s = state.samples;
  if (s.length > 1) {
    const ref = s.find((x) => x.t >= now - 5 * 60 * 1000) || s[0];
    const d = s.at(-1).soil - ref.soil;
    $("#a-trend").textContent = `${d >= 0 ? "naik" : "turun"} ${fmt1.format(Math.abs(d))} poin dalam ${durasi(s.at(-1).t - ref.t)}`;

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
}

function durasi(ms) {
  const s = Math.max(0, Math.floor(ms / 1000));
  if (s < 60) return `${s} dtk`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} mnt`;
  const h = Math.floor(m / 60);
  return `${h} jam ${m % 60} mnt`;
}

// ------------------------------------------------------------------ grafik (canvas, tanpa pustaka)
const SERIES = {
  soil: { max: 100, unit: "%", marks: [[AMBANG.soilWaspada, "Basah"], [AMBANG.soilJenuh, "Jenuh"]], fmt: (v) => fmt0.format(v) },
  rain: { max: 100, unit: "%", marks: [[AMBANG.rainWaspada, "Deras"]], fmt: (v) => fmt0.format(v) },
  tilt: { max: 10, unit: "°", marks: [[AMBANG.tiltWaspada, "Waspada"], [AMBANG.tiltBahaya, "Bahaya"]], fmt: (v) => fmt1.format(v) },
};

function cssVar(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }

function drawChart() {
  const cv = $("#chart"), box = cv.parentElement;
  const dpr = window.devicePixelRatio || 1, W = box.clientWidth, H = box.clientHeight;
  if (cv.width !== W * dpr || cv.height !== H * dpr) { cv.width = W * dpr; cv.height = H * dpr; }
  const c = cv.getContext("2d");
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  c.clearRect(0, 0, W, H);

  const cfg = SERIES[state.series];
  const ink2 = cssVar("--ink-2"), hair = cssVar("--hairline"), primary = cssVar("--primary"), danger = cssVar("--danger"), warn = cssVar("--warn");
  const L = 40, R = 64, T = 10, B = 26, pw = W - L - R, ph = H - T - B;
  const now = Date.now(), t0 = now - RIWAYAT_MS;
  const x = (t) => L + ((t - t0) / RIWAYAT_MS) * pw;
  const y = (v) => T + ph - (Math.min(v, cfg.max) / cfg.max) * ph;
  c.font = "12px " + cssVar("--font-text");

  // grid
  c.strokeStyle = hair; c.lineWidth = 1; c.fillStyle = ink2; c.textAlign = "right"; c.textBaseline = "middle";
  for (let i = 0; i <= 4; i++) {
    const v = (cfg.max / 4) * i, yy = Math.round(y(v)) + 0.5;
    c.globalAlpha = 0.6; c.beginPath(); c.moveTo(L, yy); c.lineTo(L + pw, yy); c.stroke(); c.globalAlpha = 1;
    c.fillText(cfg.fmt(v) + cfg.unit, L - 8, yy);
  }
  c.textAlign = "center"; c.textBaseline = "top";
  for (let m = 10; m >= 0; m -= 2) {
    const t = now - m * 60000;
    c.fillText(m === 0 ? "Sekarang" : fmtJamPendek.format(t), x(t), T + ph + 8);
  }

  // ambang
  c.setLineDash([5, 5]); c.textAlign = "left"; c.textBaseline = "middle";
  cfg.marks.forEach(([v, label], i) => {
    const col = i === cfg.marks.length - 1 && state.series !== "rain" ? danger : warn;
    c.strokeStyle = col; c.globalAlpha = 0.8;
    c.beginPath(); c.moveTo(L, y(v)); c.lineTo(L + pw, y(v)); c.stroke();
    c.globalAlpha = 1; c.fillStyle = col; c.fillText(label, L + pw + 8, y(v));
  });
  c.setLineDash([]);

  const pts = state.samples.filter((p) => p.t >= t0);
  if (pts.length < 2) {
    c.fillStyle = ink2; c.textAlign = "center"; c.fillText("Menunggu data", L + pw / 2, T + ph / 2);
    return;
  }
  // area + garis
  c.beginPath(); c.moveTo(x(pts[0].t), y(pts[0][state.series]));
  for (const p of pts) c.lineTo(x(p.t), y(p[state.series]));
  c.strokeStyle = primary; c.lineWidth = 2; c.lineJoin = "round"; c.stroke();
  c.lineTo(x(pts.at(-1).t), y(0)); c.lineTo(x(pts[0].t), y(0)); c.closePath();
  c.globalAlpha = 0.08; c.fillStyle = primary; c.fill(); c.globalAlpha = 1;

  // titik saat status bahaya (bentuk + warna, tidak hanya warna)
  c.fillStyle = danger;
  for (const p of pts) if (p.status === "bahaya") { c.beginPath(); c.arc(x(p.t), y(p[state.series]), 2.5, 0, Math.PI * 2); c.fill(); }

  // nilai terkini
  const last = pts.at(-1);
  c.fillStyle = primary; c.beginPath(); c.arc(x(last.t), y(last[state.series]), 4.5, 0, Math.PI * 2); c.fill();
  cv.setAttribute("aria-label", `Grafik ${state.series === "soil" ? "kelembapan tanah" : state.series === "rain" ? "intensitas hujan" : "pergeseran kemiringan"} 10 menit terakhir, nilai sekarang ${cfg.fmt(last[state.series])}${cfg.unit}`);
}

// ------------------------------------------------------------------ koneksi
function setConn(c) {
  state.conn = c;
  const el = $("#conn");
  el.dataset.state = c;
  $("#conn-text").textContent = {
    demo: "Mode demo: data simulasi",
    connecting: "Menyambung ke perangkat…",
    live: "Terhubung ke perangkat",
    stale: "Perangkat tidak mengirim data",
    offline: "Server terputus, mencoba lagi…",
  }[c];
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
    ws.onopen = () => { retry = 1000; setConn(state.lastAt && Date.now() - state.lastAt < BASI_MS ? "live" : "stale"); };
    ws.onmessage = (m) => {
      const msg = JSON.parse(m.data);
      if (msg.type === "hello") {
        for (const h of msg.history || []) ingestTelemetry(h.data, h.ts);
        for (const e of (msg.events || []).slice().reverse()) ingestEvent(e.data, e.ts);
        if (!state.lastAt) setConn("stale");
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
  document.querySelectorAll("[data-preset]").forEach((b) => b.addEventListener("click", () => {
    const [a, b2, c] = preset[b.dataset.preset]; setSoil(a); setRain(b2); setTilt(c);
  }));
  $("#btn-calib").addEventListener("click", () => {
    baseline = input.tilt; penilai = new PenilaiStatus();
    ingestEvent({ event: "kalibrasi_ulang" });
    setStatus("aman", Date.now(), false);
  });

  ingestEvent({ event: "boot" }, mulai);
  ingestEvent({ event: "baseline_siap" }, mulai + 2000);

  setInterval(() => {
    const now = Date.now();
    for (const k of ["soil", "rain", "tilt"]) f[k] = 0.3 * input[k] + 0.7 * f[k];
    const p = { soil: f.soil, rain: f.rain, tilt: Math.max(0, f.tilt - baseline) };
    const sebelum = penilai.s;
    if (penilai.perbarui(kandidat(p), now)) {
      ingestEvent({ event: "status_change", from: NAMA[sebelum], to: NAMA[penilai.s] }, now);
    }
    const interval = [2000, 1000, 500][penilai.s];
    if (now - tKirim >= interval) {
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
document.querySelectorAll(".segmented button").forEach((b) => b.addEventListener("click", () => {
  state.series = b.dataset.series;
  document.querySelectorAll(".segmented button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
  drawChart();
}));

$("#btn-sound").addEventListener("click", (e) => {
  state.sound = !state.sound;
  if (state.sound && !audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  e.currentTarget.setAttribute("aria-pressed", String(state.sound));
  e.currentTarget.textContent = `Bunyi alarm: ${state.sound ? "nyala" : "mati"}`;
  if (state.sound && state.status === "bahaya") startAlarm(); else if (!state.sound) stopAlarm();
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
