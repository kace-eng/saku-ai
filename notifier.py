"""Pengingat otomatis untuk SakuAI: notifikasi Android lewat Termux:API (tanpa Telegram/akun apa pun).

Pakai:
  python notifier.py            # jalan terus, cek tiap 15 menit
  python notifier.py --sekali   # cek satu kali lalu selesai
  python notifier.py --uji      # kirim satu notifikasi percobaan
"""
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from datetime import date, datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from core import config, indeks, pola, skema  # noqa: E402

URL_APP = f"http://127.0.0.1:{os.environ.get('PORT', '8000')}"
INTERVAL_MENIT = int(os.environ.get("NOTIF_INTERVAL_MIN", "15"))
JAM_SENYAP = (int(os.environ.get("NOTIF_SENYAP_MULAI", "22")), int(os.environ.get("NOTIF_SENYAP_AKHIR", "6")))
JAM_RINGKASAN = int(os.environ.get("NOTIF_JAM_RINGKASAN", "7"))
TAHAP = (3, 1, 0)  # H-3, H-1, hari H; setelah lewat: tiap hari sampai ditandai selesai


def kirim(judul, isi, notif_id, batal_url=None):
    """Kirim notifikasi. Bila Termux:API tidak ada, cetak ke layar."""
    if shutil.which("termux-notification"):
        try:
            cmd = ["termux-notification", "--id", str(notif_id), "--title", judul, "--content", isi,
                   "--priority", "high", "--action", f"termux-open-url {URL_APP}"]
            if batal_url:  # tombol di notifikasi: satu ketukan membatalkan catatan otomatis
                cmd += ["--button1", "BATALKAN", "--button1-action", f"curl -s -X POST {batal_url}"]
            subprocess.run(cmd, timeout=15, check=False)
            return True
        except (subprocess.SubprocessError, OSError) as e:
            print(f"[notifier] gagal kirim: {e}")
            return False
    print(f"[notifier] (tanpa Termux:API) {judul} — {isi}")
    return True


def _db():
    conn = sqlite3.connect(config.APP_DB)
    skema.pastikan(conn)
    return conn


def jam_senyap(sekarang):
    m, a = JAM_SENYAP
    return (sekarang.hour >= m or sekarang.hour < a) if m > a else (m <= sekarang.hour < a)


def label(sisa):
    if sisa < 0:
        return f"terlambat {abs(sisa)} hari"
    return "HARI INI" if sisa == 0 else f"{sisa} hari lagi"


def cek_sekali(sekarang=None):
    """Kembalikan jumlah notifikasi yang dikirim pada pengecekan ini."""
    sekarang = sekarang or datetime.now()
    if jam_senyap(sekarang):
        return 0
    hari_ini = sekarang.date()
    terkirim = 0
    with closing(_db()) as conn, conn:
        def sudah(kunci):
            return conn.execute("SELECT 1 FROM notif_log WHERE kunci=?", (kunci,)).fetchone() is not None

        def tandai(kunci):
            conn.execute("INSERT OR IGNORE INTO notif_log VALUES (?, ?)", (kunci, sekarang.isoformat()))

        # 1) Pola berulang -> pengingat otomatis (sekali sehari)
        kunci = f"pola:{hari_ini.isoformat()}"
        if not sudah(kunci):
            for p in pola.buat_pengingat_otomatis(conn, hari_ini):
                if kirim("🔁 Pengingat otomatis", f"{p['judul']} — sekitar {p['jatuh_tempo']}", 3000 + terkirim):
                    terkirim += 1
            tandai(kunci)

        # 2) Anggaran hampir/lewat batas (sekali per kategori, per level, per bulan)
        bulan = hari_ini.strftime("%Y-%m")
        for i, a in enumerate(indeks.status_anggaran(conn, hari_ini)):
            if a["status"] == "aman":
                continue
            level = 100 if a["status"] == "lewat" else 80
            kunci = f"ang:{a['kategori']}:{bulan}:{level}"
            if not sudah(kunci):
                judul = f"🚫 Anggaran {a['kategori']} terlampaui" if level == 100 else f"⚠️ Anggaran {a['kategori']} hampir habis"
                isi = f"Terpakai Rp {a['pakai']:,.0f} dari Rp {a['batas']:,.0f} ({a['persen']:.0f}%)".replace(",", ".")
                if kirim(judul, isi, 2000 + i):
                    tandai(kunci)
                    terkirim += 1

        # 3) Sisa dana menipis (maksimal sekali seminggu)
        ik = indeks.hitung(conn, hari_ini)
        minggu = hari_ini.strftime("%G-W%V")
        kunci = f"runway:{minggu}"
        if ik["level"] == "Rawan" and not sudah(kunci):
            if kirim("🪫 Sisa dana menipis", f"Dengan pola sekarang, dana bertahan ±{ik['runway_hari']} hari.", 4000):
                tandai(kunci)
                terkirim += 1

        rows = conn.execute(
            "SELECT id, judul, jatuh_tempo FROM pengingat WHERE status='AKTIF' ORDER BY jatuh_tempo").fetchall()
        aktif = []
        for rid, judul, tempo in rows:
            try:
                sisa = (datetime.strptime(tempo, "%Y-%m-%d").date() - hari_ini).days
            except (ValueError, TypeError):
                continue
            aktif.append((rid, judul, sisa))
            if sisa in TAHAP or sisa < 0:
                kunci = f"rem:{rid}:{hari_ini.isoformat()}"
                if not sudah(kunci):
                    ikon = "🚨" if sisa <= 0 else "⏰"
                    if kirim(f"{ikon} {judul}", f"Jatuh tempo: {tempo} ({label(sisa)})", 1000 + rid):
                        tandai(kunci)
                        terkirim += 1

        # Ringkasan pagi, sekali sehari
        kunci = f"ringkasan:{hari_ini.isoformat()}"
        if sekarang.hour >= JAM_RINGKASAN and not sudah(kunci):
            dekat = [f"{j} ({label(s)})" for _, j, s in aktif if s <= 7][:3]
            isi = ("Jadwal dekat: " + "; ".join(dekat)) if dekat else "Tidak ada jadwal mendesak. 👍"
            if kirim("🌅 SakuAI — ringkasan hari ini", isi, 1):
                tandai(kunci)
                terkirim += 1
    return terkirim


def main():
    if "--uji" in sys.argv:
        kirim("✅ SakuAI aktif", "Notifikasi berhasil. Pengingat akan muncul di sini.", 1)
        return
    if "--sekali" in sys.argv:
        print(f"[notifier] {cek_sekali()} notifikasi dikirim.")
        return
    print(f"[notifier] berjalan, cek tiap {INTERVAL_MENIT} menit. Ctrl+C untuk berhenti.")
    while True:
        try:
            n = cek_sekali()
            if n:
                print(f"[notifier] {datetime.now():%H:%M} {n} notifikasi dikirim.")
        except Exception as e:  # jangan sampai daemon mati karena satu error
            print(f"[notifier] error: {e}")
        time.sleep(INTERVAL_MENIT * 60)


if __name__ == "__main__":
    main()
