"""Penangkap transaksi otomatis: membaca notifikasi bank/e-wallet di HP lalu mencatatnya sendiri.

Aman & opsional: hanya paket aplikasi yang Anda daftarkan di .env (AUTO_PAKET), semua diproses lokal tanpa AI.
  python penangkap.py --daftar        # lihat nama paket dari notifikasi yang sedang tampil
  python penangkap.py --uji "teks"    # uji pembacaan satu teks notifikasi
  python penangkap.py --sekali        # satu kali pengecekan
  python penangkap.py                 # jalan terus
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from datetime import date, datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from core import config, notifparse, parser, skema  # noqa: E402
from core.engine import SovereignEngine  # noqa: E402
import notifier  # noqa: E402

INTERVAL_DETIK = int(os.environ.get("AUTO_INTERVAL_DETIK", "30"))
URL_APP = notifier.URL_APP


def paket_diizinkan():
    return {p.strip() for p in os.environ.get("AUTO_PAKET", "").split(",") if p.strip()}


def ambil_notifikasi():
    if not shutil.which("termux-notification-list"):
        raise RuntimeError("termux-notification-list tidak ada. Jalankan: pkg install termux-api")
    out = subprocess.run(["termux-notification-list"], capture_output=True, text=True, timeout=20).stdout
    return json.loads(out) if out.strip() else []


def proses(notifs, diizinkan, sekarang=None, engine=None, kirim_notif=True):
    """Catat transaksi dari daftar notifikasi. Kembalikan daftar yang berhasil dicatat."""
    sekarang = sekarang or datetime.now()
    engine = engine or SovereignEngine()
    tercatat = []
    with closing(sqlite3.connect(config.APP_DB)) as conn, conn:
        skema.pastikan(conn)
        conn.execute("DELETE FROM jejak_otomatis WHERE ts < ?", (time.time() - 7 * 86400,))
        for n in notifs:
            pkg = n.get("packageName", "")
            if pkg not in diizinkan:
                continue
            t = notifparse.baca(n.get("title"), n.get("content"))
            if not t:
                continue
            kunci = hashlib.sha256(f"{pkg}|{n.get('key')}|{n.get('when')}|{n.get('title')}|{n.get('content')}".encode()).hexdigest()
            ringkas = f"{t['jenis']}|{t['nominal']:.0f}|{t['label'].lower()}"
            if conn.execute("SELECT 1 FROM jejak_otomatis WHERE kunci=? OR (ringkas=? AND ts > ?)",
                            (kunci, ringkas, time.time() - 120)).fetchone():
                continue  # notifikasi yang sama / pengiriman ulang oleh aplikasi
            label = engine.sanitize_privacy(t["label"])
            hari_ini = sekarang.date().isoformat()
            if t["jenis"] == "keluar":
                kat = parser._kategori(f"{n.get('title')} {n.get('content')}")
                cur = conn.execute("INSERT INTO pengeluaran (tanggal, kategori, keterangan, nominal, bukti_hash) VALUES (?,?,?,?,?)",
                                   (hari_ini, kat, f"🤖 {label}", t["nominal"], ""))
                batal = f"{URL_APP}/hapus-pengeluaran/{cur.lastrowid}"
                engine.record_decision("Penangkap", f"Auto: {label}", [t["nominal"]], enforce_audit=False)
            else:
                cur = conn.execute("INSERT INTO pemasukan (tanggal, sumber, nominal) VALUES (?,?,?)",
                                   (hari_ini, f"🤖 {label}", t["nominal"]))
                batal = f"{URL_APP}/hapus-pemasukan/{cur.lastrowid}"
            conn.execute("INSERT INTO jejak_otomatis VALUES (?,?,?)", (kunci, time.time(), ringkas))
            item = {"id": cur.lastrowid, **t, "label": label}
            tercatat.append(item)
            if kirim_notif and not notifier.jam_senyap(sekarang):
                arah = "Keluar" if t["jenis"] == "keluar" else "Masuk"
                notifier.kirim("🤖 Tercatat otomatis", f"{arah} Rp {t['nominal']:,.0f} — {label}".replace(",", "."),
                               5000 + cur.lastrowid % 900, batal_url=batal)
    return tercatat


def main():
    if "--uji" in sys.argv:
        teks = sys.argv[sys.argv.index("--uji") + 1] if len(sys.argv) > sys.argv.index("--uji") + 1 else ""
        print(notifparse.baca("", teks) or "Bukan transaksi (akan diabaikan).")
        return
    if "--daftar" in sys.argv:
        try:
            data = ambil_notifikasi()
        except Exception as e:
            print(f"Gagal: {e}")
            return
        if not data:
            print("Tidak ada notifikasi terbaca. Pastikan izin 'Akses notifikasi' untuk Termux:API sudah aktif.")
        for n in data:
            print(f"{n.get('packageName')}  |  {n.get('title')}")
        return

    diizinkan = paket_diizinkan()
    if not diizinkan:
        print("[penangkap] nonaktif: AUTO_PAKET di .env masih kosong (jalankan 'python penangkap.py --daftar').")
        return
    if "--sekali" in sys.argv:
        print(f"[penangkap] {len(proses(ambil_notifikasi(), diizinkan))} transaksi dicatat.")
        return
    print(f"[penangkap] berjalan untuk {len(diizinkan)} aplikasi, cek tiap {INTERVAL_DETIK} detik.")
    while True:
        try:
            for t in proses(ambil_notifikasi(), diizinkan):
                print(f"[penangkap] {datetime.now():%H:%M} {t['jenis']} Rp{t['nominal']:,.0f} {t['label']}")
        except Exception as e:
            print(f"[penangkap] error: {e}")
        time.sleep(INTERVAL_DETIK)


if __name__ == "__main__":
    main()
