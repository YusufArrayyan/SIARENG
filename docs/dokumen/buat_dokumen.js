// Membuat laporan dan lembar jawaban berformat modul Teknologi IoT FT UNIB (.docx),
// lalu mengekspor PDF lewat Microsoft Word.
//
//   cd docs/dokumen && npm install && node buat_dokumen.js
//
// Sumber isi: berkas Markdown di folder sumber/. Setiap berkas diawali blok metadata:
//   ---
//   berkas: Laporan_Lab1_Minggu02          (nama keluaran tanpa ekstensi)
//   jenis: LAPORAN PRAKTIKUM | LEMBAR JAWABAN
//   unit: LAB. JARINGAN & | SISTEM TERTANAM   (baris dipisah "|")
//   judul: LAPORAN PRAKTIKUM MINGGU KE-2
//   subjudul: GPIO Digital/Analog, PWM, DHT22, & Soil Moisture
//   kolom: Kode Lab=Lab-1 (Bobot 2%) | Minggu=2 dari 16 | Sub-CPMK=Sub-CPMK 1.2
//   kepala_kiri: Laporan Praktikum Minggu 2 — Teknologi IoT
//   kepala_kanan: Lab-1: GPIO, ADC, PWM, DHT22, & Soil Moisture
//   kaki: Laboratorium Jaringan Komputer & Sistem Tertanam FT UNIB
//   ---
// Sintaks isi: "## " pita BAGIAN, "### " subjudul, "> " kotak biru (soal/tujuan),
// ">! " kotak kuning (catatan), tabel Markdown, ``` kode ``` diikuti baris "Listing: ..." (opsional),
// "- " butir, "1. " nomor, **tebal**, *miring*, `kode`, <sub>, <sup>.

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, AlignmentType, VerticalAlign, Header, Footer, PageNumber, TabStopType,
  LevelFormat, TableLayoutType, HeightRule,
} = require("docx");

const NAVY = "17365D";
const BIRU_MUDA = "DCE6F2";
const BIRU_KOTAK = "EAF1FB";
const KUNING = "FFF4DC";
const ABU_KODE = "F4F4F4";
const HITAM = "000000";
const FONT = "Times New Roman";
const MONO = "Consolas";
const LEBAR = 9638;          // A4 dikurangi margin 2 × 2 cm, dalam DXA
const UKURAN = 21;           // 10,5 pt (setengah poin)

const tipis = { style: BorderStyle.SINGLE, size: 4, color: HITAM };
const garis = { top: tipis, bottom: tipis, left: tipis, right: tipis };
const tanpa = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const tanpaGaris = { top: tanpa, bottom: tanpa, left: tanpa, right: tanpa };

// ------------------------------------------------------------------ teks inline
function runs(teks, dasar = {}) {
  const out = [];
  // tautan Markdown -> teks saja
  teks = teks.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
  const re = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`|<sub>[^<]+<\/sub>|<sup>[^<]+<\/sup>|<br>)/g;
  let i = 0, m;
  const tambah = (t, o = {}) => t && out.push(new TextRun({ text: t, font: FONT, size: UKURAN, ...dasar, ...o }));
  while ((m = re.exec(teks))) {
    tambah(teks.slice(i, m.index));
    const s = m[0];
    if (s.startsWith("**")) out.push(...runs(s.slice(2, -2), { ...dasar, bold: true }));
    else if (s.startsWith("`")) tambah(s.slice(1, -1), { font: MONO, size: UKURAN - 3 });
    else if (s.startsWith("<sub>")) tambah(s.slice(5, -6), { subScript: true });
    else if (s.startsWith("<sup>")) tambah(s.slice(5, -6), { superScript: true });
    else if (s === "<br>") out.push(new TextRun({ break: 1 }));
    else out.push(...runs(s.slice(1, -1), { ...dasar, italics: true }));
    i = m.index + s.length;
  }
  tambah(teks.slice(i));
  return out;
}

const para = (teks, o = {}) => new Paragraph({
  children: runs(teks, o.run || {}), alignment: o.align ?? AlignmentType.JUSTIFIED,
  spacing: { before: o.before ?? 0, after: o.after ?? 100, line: 264 }, keepNext: o.keepNext,
  indent: o.indent, numbering: o.numbering,
});

function sel(isi, w, o = {}) {
  const daftar = Array.isArray(isi) ? isi : [isi];
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: o.borders || garis,
    shading: o.fill ? { type: ShadingType.CLEAR, color: "auto", fill: o.fill } : undefined,
    verticalAlign: o.valign || VerticalAlign.CENTER,
    columnSpan: o.span, rowSpan: o.rowSpan,
    margins: { top: 50, bottom: 50, left: 100, right: 100 },
    children: daftar.map((x) => (x instanceof Paragraph ? x : para(x, { align: o.align ?? AlignmentType.LEFT, after: 0, run: o.run, keepNext: o.keepNext }))),
  });
}

// ------------------------------------------------------------------ blok besar
function kepalaDokumen(meta) {
  const kolom = meta.kolom.split("|").map((s) => s.trim().split("="));
  const w = [2150, 3788, 1450, 2250];
  const putih = { color: "FFFFFF", bold: true };
  const unit = meta.unit.split("|").map((s) => s.trim());
  const kiri = [
    para(`**${unit[0]}**`, { align: AlignmentType.CENTER, after: 0 }),
    ...unit.slice(1).map((u, i) => para(i === 0 ? `**${u}**` : u, { align: AlignmentType.CENTER, after: 0, run: { size: 19 } })),
  ];
  const tengah = [
    para(`**${meta.judul}**`, { align: AlignmentType.CENTER, after: 20, run: { size: 23 } }),
    para("**Teknologi Internet of Things (IoT)**", { align: AlignmentType.CENTER, after: 20 }),
    para(meta.subjudul, { align: AlignmentType.CENTER, after: 0, run: { size: 19 } }),
  ];
  const baris = [
    new TableRow({ children: [
      sel("UNIVERSITAS BENGKULU — FAKULTAS TEKNIK", w[0] + w[1], { span: 2, fill: NAVY, align: AlignmentType.CENTER, run: putih }),
      sel(meta.jenis, w[2] + w[3], { span: 2, fill: NAVY, align: AlignmentType.CENTER, run: putih }),
    ] }),
  ];
  kolom.forEach(([k, v], i) => {
    const isi = [sel(`**${k}**`, w[2], { fill: BIRU_MUDA }), sel(v, w[3])];
    if (i === 0) isi.unshift(sel(kiri, w[0], { rowSpan: kolom.length }), sel(tengah, w[1], { rowSpan: kolom.length }));
    baris.push(new TableRow({ children: isi }));
  });
  return new Table({ width: { size: LEBAR, type: WidthType.DXA }, columnWidths: w, rows: baris, layout: TableLayoutType.FIXED });
}

function pita(teks) {
  return new Table({
    width: { size: LEBAR, type: WidthType.DXA }, columnWidths: [LEBAR], layout: TableLayoutType.FIXED,
    rows: [new TableRow({ cantSplit: true, children: [sel(teks.toUpperCase(), LEBAR, {
      fill: NAVY, borders: tanpaGaris, run: { color: "FFFFFF", bold: true, size: 23 }, keepNext: true,
    })] })],
  });
}

function kotak(barisTeks, fill, tepi) {
  const g = { style: BorderStyle.SINGLE, size: 6, color: tepi };
  const isi = [];
  for (const b of barisTeks) {
    if (/^\s*[-*] /.test(b)) isi.push(para(b.replace(/^\s*[-*] /, ""), { numbering: { reference: "butir", level: 0 }, after: 40 }));
    else if (/^\s*\d+\. /.test(b)) isi.push(para(b.replace(/^\s*\d+\. /, ""), { numbering: { reference: "nomor-kotak", level: 0 }, after: 40 }));
    else if (b.trim()) isi.push(para(b, { after: 60 }));
  }
  return new Table({
    width: { size: LEBAR, type: WidthType.DXA }, columnWidths: [LEBAR], layout: TableLayoutType.FIXED,
    rows: [new TableRow({ children: [new TableCell({
      width: { size: LEBAR, type: WidthType.DXA }, borders: { top: g, bottom: g, left: g, right: g },
      shading: { type: ShadingType.CLEAR, color: "auto", fill }, margins: { top: 90, bottom: 40, left: 140, right: 140 },
      children: isi,
    })] })],
  });
}

function tabel(barisMd) {
  const sel2 = (l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
  const kepala = sel2(barisMd[0]);
  const data = barisMd.slice(2).map(sel2);
  const n = kepala.length;
  // lebar kolom sebanding panjang isi, dengan batas bawah
  const panjang = kepala.map((h, j) => Math.max(h.length, ...data.map((r) => Math.min((r[j] || "").length, 160))));
  const sempit = panjang.map((p, j) => data.every((r) => (r[j] || "").length <= 3) && kepala[j].length <= 4);
  const sisa = LEBAR - sempit.filter(Boolean).length * 620;
  const total = panjang.reduce((a, b, j) => a + (sempit[j] ? 0 : Math.sqrt(b + 6)), 0);
  let w = panjang.map((p, j) => sempit[j] ? 620 : Math.max(900, Math.round((Math.sqrt(p + 6) / total) * sisa)));
  const kor = LEBAR - w.reduce((a, b) => a + b, 0);
  w[w.indexOf(Math.max(...w))] += kor;
  const kecil = n >= 4 ? 19 : UKURAN;
  return new Table({
    width: { size: LEBAR, type: WidthType.DXA }, columnWidths: w, layout: TableLayoutType.FIXED,
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true, children: kepala.map((h, j) => sel(h.replace(/\*\*/g, ""), w[j], { fill: BIRU_MUDA, run: { size: kecil, bold: true } })) }),
      ...data.map((r) => new TableRow({ cantSplit: r.join("").length < 350, children: kepala.map((_, j) => sel(r[j] ?? "", w[j], { valign: VerticalAlign.TOP, run: { size: kecil } })) })),
    ],
  });
}

function listing(kode, keterangan) {
  const isi = kode.map((l, i) => new Paragraph({
    spacing: { before: 0, after: 0, line: 240 },
    children: [
      new TextRun({ text: String(i + 1).padStart(3, " ") + "  ", font: MONO, size: 15, color: "8C8C8C" }),
      new TextRun({ text: l.replace(/\t/g, "  ") || " ", font: MONO, size: 17 }),
    ],
  }));
  const g = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
  const out = [new Table({
    width: { size: LEBAR, type: WidthType.DXA }, columnWidths: [LEBAR], layout: TableLayoutType.FIXED,
    rows: [new TableRow({ children: [new TableCell({
      width: { size: LEBAR, type: WidthType.DXA }, borders: { top: g, bottom: g, left: g, right: g },
      shading: { type: ShadingType.CLEAR, color: "auto", fill: ABU_KODE }, margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: isi,
    })] })],
  })];
  if (keterangan) out.push(para(keterangan, { align: AlignmentType.CENTER, before: 60, after: 160, run: { size: 19 } }));
  else out.push(para("", { after: 80 }));
  return out;
}

// ------------------------------------------------------------------ pengurai Markdown sederhana
function urai(teks) {
  const baris = teks.replace(/\r/g, "").split("\n");
  const blok = [];
  let nomorList = 0;
  for (let i = 0; i < baris.length; i++) {
    const l = baris[i];
    if (!l.trim() || l.trim() === "---") continue;
    if (l.startsWith("# ")) continue;                               // judul diganti kepala dokumen
    if (l.startsWith("## ")) { blok.push(para("", { after: 40, keepNext: true }), pita(l.slice(3)), para("", { after: 60, keepNext: true })); continue; }
    if (l.startsWith("### ")) { blok.push(para(l.slice(4), { before: 160, after: 80, keepNext: true, run: { size: 23, bold: true } })); continue; }
    if (l.startsWith("```")) {
      const kode = [];
      while (++i < baris.length && !baris[i].startsWith("```")) kode.push(baris[i]);
      let ket = null;
      if (baris[i + 1] && baris[i + 1].startsWith("Listing")) ket = baris[++i];
      blok.push(...listing(kode, ket));
      continue;
    }
    if (l.startsWith(">")) {
      const isi = [];
      const catatan = l.startsWith(">!");
      while (i < baris.length && baris[i].startsWith(">")) { isi.push(baris[i].replace(/^>!?\s?/, "")); i++; }
      i--;
      blok.push(kotak(isi, catatan ? KUNING : BIRU_KOTAK, catatan ? "C9A227" : NAVY), para("", { after: 60 }));
      continue;
    }
    if (l.startsWith("|")) {
      const t = [];
      while (i < baris.length && baris[i].startsWith("|")) t.push(baris[i++]);
      i--;
      blok.push(tabel(t), para("", { after: 80 }));
      continue;
    }
    if (/^\s*[-*] /.test(l)) {
      const lvl = l.match(/^\s*/)[0].length >= 2 ? 1 : 0;
      blok.push(para(l.replace(/^\s*[-*] /, ""), { numbering: { reference: "butir", level: lvl }, after: 50 }));
      continue;
    }
    const mn = l.match(/^(\d+)\. (.*)/);
    if (mn) {
      if (mn[1] === "1") nomorList++;
      blok.push(para(mn[2], { numbering: { reference: "nomor", level: 0, instance: nomorList }, after: 50 }));
      continue;
    }
    blok.push(para(l));
  }
  return blok;
}

function bacaMeta(teks) {
  const m = teks.match(/^---\n([\s\S]*?)\n---\n/);
  const meta = {};
  m[1].split("\n").forEach((l) => { const k = l.indexOf(":"); meta[l.slice(0, k).trim()] = l.slice(k + 1).trim(); });
  return { meta, isi: teks.slice(m[0].length) };
}

// ------------------------------------------------------------------ dokumen
function buat(berkasMd, folderKeluar) {
  const { meta, isi } = bacaMeta(fs.readFileSync(berkasMd, "utf8").replace(/\r/g, ""));
  const tabKanan = [{ type: TabStopType.RIGHT, position: LEBAR }];
  const doc = new Document({
    creator: "Kelompok SIARENG",
    title: `${meta.judul} — ${meta.subjudul}`,
    styles: { default: { document: { run: { font: FONT, size: UKURAN } } } },
    numbering: { config: [
      { reference: "butir", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 400, hanging: 240 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 800, hanging: 240 } } } },
      ] },
      { reference: "nomor", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 420, hanging: 300 } } } }] },
      { reference: "nomor-kotak", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 420, hanging: 300 } } } }] },
    ] },
    sections: [{
      properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, bottom: 1200, left: 1134, right: 1134, header: 560, footer: 560 } } },
      headers: { default: new Header({ children: [new Paragraph({
        tabStops: tabKanan, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: HITAM, space: 2 } },
        children: [
          new TextRun({ text: meta.kepala_kiri, font: FONT, size: 17, bold: true }),
          new TextRun({ text: " | Prodi S1 Informatika FT UNIB", font: FONT, size: 17 }),
          new TextRun({ text: "\t" + meta.kepala_kanan, font: FONT, size: 17 }),
        ],
      })] }) },
      footers: { default: new Footer({ children: [new Paragraph({
        tabStops: tabKanan, border: { top: { style: BorderStyle.SINGLE, size: 4, color: HITAM, space: 2 } },
        children: [
          new TextRun({ text: meta.kaki, font: FONT, size: 17 }),
          new TextRun({ text: "\tHalaman ", font: FONT, size: 17 }),
          new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 17 }),
          new TextRun({ text: " dari ", font: FONT, size: 17 }),
          new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: 17, color: NAVY }),
        ],
      })] }) },
      children: [kepalaDokumen(meta), para("", { after: 120 }), ...urai(isi)],
    }],
  });
  return Packer.toBuffer(doc).then((buf) => {
    const keluar = path.join(folderKeluar, meta.berkas + ".docx");
    fs.writeFileSync(keluar, buf);
    return keluar;
  });
}

function keWordPdf(daftarDocx) {
  // Satu proses Word untuk semua berkas: buka, simpan sebagai PDF (format 17), tutup.
  const ps = [
    "$ErrorActionPreference='Stop'",
    "$w = New-Object -ComObject Word.Application", "$w.Visible = $false",
    ...daftarDocx.map((f) => {
      const pdf = f.replace(/\.docx$/, ".pdf");
      return `$d = $w.Documents.Open('${f}', $false, $true); $d.Fields.Update() | Out-Null; $d.SaveAs2('${pdf}', 17); $d.Close($false)`;
    }),
    "$w.Quit()",
  ].join("; ");
  execFileSync("powershell", ["-NoProfile", "-Command", ps], { stdio: "inherit" });
}

(async () => {
  const sumber = path.join(__dirname, "sumber");
  const keluar = path.join(__dirname, "..", "laporan");
  fs.mkdirSync(keluar, { recursive: true });
  const pilih = process.argv.slice(2);
  const md = fs.readdirSync(sumber).filter((f) => f.endsWith(".md") && (!pilih.length || pilih.some((p) => f.includes(p)))).sort();
  const hasil = [];
  for (const f of md) {
    hasil.push(path.resolve(await buat(path.join(sumber, f), keluar)));
    console.log("docx:", path.basename(hasil.at(-1)));
  }
  if (!process.env.TANPA_PDF) { keWordPdf(hasil); console.log("PDF selesai"); }
})();
