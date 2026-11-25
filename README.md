# 🤖 SakuAI — Asisten Pribadi Mandiri (Pengeluaran + Pengingat + Privacy Guardrail)

Aplikasi web (PWA, *Neo-Brutalism UI*) yang mengubah catatan bahasa sehari-hari atau foto struk menjadi
rekap pengeluaran, pengingat jadwal, dan catatan — dengan sensor privasi otomatis sebelum data dikirim ke AI.

## ✨ Fitur
- **Input pintar:** ketik santai ("Ganti oli 65rb, ingatkan servis 2 bulan lagi"), upload foto/galeri, PDF, file TXT/CSV, atau dikte suara.
- **Privacy guardrail:** nomor HP, email, dan nomor rekening/NIK disensor sebelum dikirim ke AI (teks & isi TXT/CSV; foto dan PDF dikirim apa adanya).
- **Cadangan offline:** bila AI/internet bermasalah, catatan teks tetap diproses parser lokal.
- **Belajar otomatis (pola berulang):** item yang sama dicatat ≥3 kali dengan selang teratur (ganti oli tiap ±60 hari, token listrik tiap 18 hari) dikenali, lalu pengingat dibuat sendiri H-7 sebelum perkiraan tanggalnya, tanpa duplikat dengan pengingat buatan Anda.
- **Catat pemasukan:** ketik "gaji masuk 3jt" atau "hp bekas laku 1,2 juta"; saldo bertambah otomatis dan bisa dibatalkan dengan menghapus entrinya di tab Keuangan.
- **Indeks Kemandirian:** isi saldo sekali; pengeluaran otomatis mengurangi dan pemasukan menambah saldo. Dihitung sisa hari bertahan (Rawan <30 hari, Waspada <90, Cukup <180, Kuat), tren dibanding bulan lalu, proyeksi akhir bulan, dan perkiraan sisa pemasukan.
- **Batas anggaran:** per kategori atau TOTAL; peringatan langsung di aplikasi dan notifikasi Android pada 80% dan 100%.
- **Dashboard:** total pengeluaran (keseluruhan & bulan ini), jadwal berkode warna, catatan, ekspor CSV (Excel).
- **Tanya memori:** "Berapa pengeluaran makan bulan ini?" dijawab dari data Anda sendiri.
- **Anti-duplikat nota** dan **ledger berantai** (hash) untuk jejak audit; cek lewat `/verifikasi`.
- **Co-Pilot terminal:** `python copilot.py "pertanyaan" file.py`
- **Bisa di-install** ke layar utama HP (Chrome → menu → *Install app*).

## 🚀 Cara menjalankan (Termux maupun laptop)
```bash
pip install -r requirements.txt
cp .env.example .env        # lalu isi GEMINI_API_KEY di dalamnya
python api/main.py
```
Buka `http://127.0.0.1:8000`.

Tanpa `GEMINI_API_KEY`, aplikasi tetap jalan memakai parser lokal untuk teks (scan foto & "Tanya memori" butuh AI).

## 🔔 Pengingat otomatis di Android (tanpa Telegram, tanpa internet)
Notifikasi muncul langsung di bar notifikasi HP lewat **Termux:API**.
1. Pasang aplikasi **Termux:API** (dari F-Droid, sumber yang sama dengan Termux Anda), lalu di Termux: `pkg install termux-api`
2. Uji: `python notifier.py --uji` (notifikasi percobaan harus muncul)
3. Jalankan semuanya sekaligus: `sh start.sh` (server + pengingat; layar boleh dimatikan)
4. Android: *Setelan → Baterai → Termux → Tanpa pembatasan*, agar proses tidak dimatikan sistem.
5. Opsional, nyala otomatis saat HP hidup: pasang **Termux:Boot**, lalu
   `mkdir -p ~/.termux/boot && cp termux/boot-saku.sh ~/.termux/boot/saku.sh`

Aturan notifikasi: H-3, H-1, hari H, lalu tiap hari bila terlambat; ringkasan pagi jam 07:00; pengingat otomatis dari pola; anggaran 80%/100% (sekali per bulan per kategori); peringatan dana menipis (maksimal seminggu sekali); senyap jam 22:00–06:00.
Ubah lewat `.env`: `NOTIF_INTERVAL_MIN`, `NOTIF_SENYAP_MULAI`, `NOTIF_SENYAP_AKHIR`, `NOTIF_JAM_RINGKASAN`.

## ⚙️ Pengaturan (`.env`)
| Variabel | Fungsi | Bawaan |
|---|---|---|
| `GEMINI_API_KEY` | Kunci API Gemini | — |
| `GEMINI_MODEL` | Model Gemini | `gemini-3.5-flash-lite` |
| `HOST` / `PORT` | Alamat server | `127.0.0.1` / `8000` |
| `LEDGER_SALT` | Garam hash ledger | nilai bawaan lama |

> ⚠️ Aplikasi belum memiliki login. Jangan set `HOST=0.0.0.0` di jaringan publik/WiFi umum.

## 🔄 Sinkronisasi HP ↔ Laptop
Kode disimpan di GitHub; data pribadi (`.env`, `database/*.db`) sengaja **tidak** ikut.
```bash
# di HP (Termux), di dalam folder proyek:
git pull
pip install -r requirements.txt
```
Laptop: ubah kode, `git push`. HP: `git pull`. Selalu tekan `Ctrl+C` lalu jalankan ulang `sh start.sh` setelah update.

## 🧪 Pengembangan
```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```
CI GitHub Actions menjalankan test yang sama di setiap push.

## 🗂️ Struktur
```
api/main.py      server Flask + endpoint
core/engine.py   sensor privasi + ledger hash berantai
core/gemini.py   klien Gemini
core/parser.py   parser lokal cadangan
core/pola.py     deteksi pola berulang + pengingat otomatis
core/indeks.py   indeks kemandirian + anggaran
core/skema.py    skema database
notifier.py      pengingat otomatis (notifikasi Android via Termux:API)
start.sh         jalankan server + pengingat sekaligus
web/             antarmuka PWA
tests/           test otomatis (pytest)
database/        file SQLite (dibuat otomatis, tidak ikut git)
```
