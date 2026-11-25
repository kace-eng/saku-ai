"""Catat lewat suara tanpa membuka aplikasi: ketuk pintasan di layar utama, bicara, selesai.
Dipasang sebagai widget oleh termux/pasang.sh.  Uji tanpa mikrofon: python catat_suara.py --teks "bensin 30rb"
"""
import os
import shutil
import subprocess
import sys

import requests

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import notifier  # noqa: E402


def dengarkan():
    if not shutil.which("termux-speech-to-text"):
        raise RuntimeError("termux-speech-to-text tidak ada. Jalankan: pkg install termux-api")
    out = subprocess.run(["termux-speech-to-text"], capture_output=True, text=True, timeout=60).stdout
    baris = [b.strip() for b in out.splitlines() if b.strip()]
    return baris[-1] if baris else ""


def ringkas(data):
    h, bagian = data.get("hasil", {}), []
    rupiah = lambda n: f"Rp {n:,.0f}".replace(",", ".")
    for p in h.get("pengeluaran", []):
        bagian.append(f"Keluar {rupiah(p['nominal'])} ({p['keterangan']})")
    for p in h.get("pemasukan", []):
        bagian.append(f"Masuk {rupiah(p['nominal'])} ({p['sumber']})")
    for p in h.get("pengingat", []):
        bagian.append(f"Jadwal: {p['judul']} → {p['jatuh_tempo']}")
    if h.get("catatan"):
        bagian.append(f"{len(h['catatan'])} catatan")
    for a in data.get("peringatan", []):
        bagian.append(f"⚠️ Anggaran {a['kategori']} {a['persen']:.0f}%")
    return "; ".join(bagian) or "Tersimpan."


def jalankan(teks):
    if not teks:
        notifier.kirim("🎤 SakuAI", "Tidak terdengar. Coba lagi.", 6000)
        return 1
    try:
        res = requests.post(f"{notifier.URL_APP}/catat-pintar", json={"teks": teks}, timeout=60)
        data = res.json()
    except requests.exceptions.RequestException:
        notifier.kirim("🎤 SakuAI belum jalan", "Server mati. Jalankan: sh start.sh", 6000)
        return 1
    if res.status_code != 200:
        notifier.kirim("🎤 Gagal mencatat", data.get("pesan", "Terjadi kesalahan."), 6000)
        return 1
    notifier.kirim("✔ Tercatat", ringkas(data), 6000)
    return 0


if __name__ == "__main__":
    if "--teks" in sys.argv:
        ucapan = sys.argv[sys.argv.index("--teks") + 1]
    else:
        try:
            ucapan = dengarkan()
        except Exception as e:
            notifier.kirim("🎤 SakuAI", str(e), 6000)
            sys.exit(1)
    sys.exit(jalankan(ucapan))
