# Skenario Demo di Kelas (sekitar 5 menit)

Buka **Serial Monitor** di Wokwi. Setiap baris adalah satu paket JSON.

## Persiapan
- Biarkan simulasi berjalan 2 detik. Muncul `{"event":"baseline_siap"...}` dan LED hijau menyala.
- Kalau slider MPU6050 sudah digeser sebelum itu, tekan tombol biru (GPIO 15) untuk kalibrasi ulang.

## Kontrol

| Kontrol di Wokwi | Arti |
|---|---|
| Potensiometer `pot_soil` | Kanan = tanah basah (kiri = kering) |
| Potensiometer `pot_rain` | Kanan = hujan deras |
| Klik MPU6050 -> slider **Acceleration X** | Menggeser kemiringan. Bandingkan dengan Z: **ax = 0,10 x az** setara sekitar 6 derajat, **ax = 0,05 x az** sekitar 3 derajat |
| Tombol biru | Kalibrasi ulang baseline kemiringan |

## Tahap demo

| Tahap | Aksi | Yang terlihat |
|---|---|---|
| 1. AMAN | Semua potensiometer di kiri, slider MPU default | LED hijau. `"status":"aman"`, data tiap 2 detik |
| 2. WASPADA (hujan) | Putar `pot_rain` ke kanan (> 40%) lalu `pot_soil` ke sekitar 65% | LED kuning, bip tiap 3 detik, data tiap 1 detik. Muncul event `status_change` aman -> waspada |
| 3. WASPADA (hanya miring) | Kembalikan potensiometer ke kiri, geser ax ke sekitar 6 derajat | Tetap `waspada` (tanah belum jenuh, jadi bukan bahaya). Ini pembeda alarm palsu |
| 4. BAHAYA | Putar `pot_soil` ke kanan penuh (> 80%) sambil ax tetap miring | Setelah 2 detik: LED merah berkedip, buzzer bunyi, `"alert":true`, data tiap 0,5 detik |
| 5. Pulih | Kembalikan semua ke awal | Setelah 6 detik status turun bertahap |

## Mengukur latensi alert (untuk laporan)
Catat `uptime_ms` baris terakhir sebelum kondisi bahaya dibuat dan `uptime_ms` pada event
`status_change` ke `bahaya`. Selisihnya mendekati 2000 ms (jeda konfirmasi) ditambah maksimal 200 ms
(interval baca sensor). Ulangi 5 kali dan laporkan rata-ratanya.

## Batasan yang wajib ditulis di laporan
- Demo menguji logika sistem, bukan kemampuan mendeteksi longsor sungguhan.
- Ambang kemiringan dan kejenuhan tanah adalah nilai awal untuk kalibrasi. Ambang nyata harus dari BNPB, PVMBG, atau kajian geologi lokal.
- Alat ini alarm lokal pelengkap, bukan sistem peringatan dini resmi, dan tidak memprediksi longsor.
