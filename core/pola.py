"""Deteksi pola pengeluaran berulang + pembuatan pengingat otomatis.

Cara kerja: keterangan pengeluaran dikelompokkan berdasarkan kata inti yang mirip
("ganti oli", "oli motor" -> kelompok "oli"). Kelompok yang muncul >= 3 kali dengan
selang waktu yang konsisten dianggap pola; tanggal berikutnya = terakhir + selang median.
"""
import re
import statistics
from collections import Counter
from datetime import date, datetime, timedelta

STOP = {"beli", "bayar", "ganti", "untuk", "di", "ke", "dan", "yang", "dg", "dengan", "rp", "ribu", "rb",
        "jt", "juta", "bulan", "minggu", "hari", "lagi", "ingatkan", "tadi", "pagi", "siang", "malam", "sore",
        "lunas", "tagihan", "biaya"}
MIN_KALI = 3          # minimal kemunculan (pada hari berbeda)
MIN_INTERVAL = 3      # abaikan kebiasaan harian (kopi tiap hari, dsb.)
MAX_KERAGAMAN = 0.30  # simpangan median selang / median selang
KEMIRIPAN = 0.5       # kemiripan kata inti untuk digabung


def tokens(teks):
    return frozenset(t for t in re.findall(r"[a-z]{2,}", str(teks).lower()) if t not in STOP)


def _mirip(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def _tgl(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def deteksi(conn, today=None):
    today = today or date.today()
    klaster = []
    for tgl, ket, nom in conn.execute("SELECT tanggal, keterangan, nominal FROM pengeluaran ORDER BY tanggal, id"):
        d, t = _tgl(tgl), tokens(ket)
        if d is None or not t:
            continue
        k = next((k for k in klaster if _mirip(t, k["inti"]) >= KEMIRIPAN), None)
        if k is None:
            k = {"inti": t, "ket": Counter(), "hari": {}}
            klaster.append(k)
        k["ket"][str(ket).strip().lower()] += 1
        k["hari"][d] = k["hari"].get(d, 0.0) + float(nom or 0)

    hasil = []
    for k in klaster:
        hari = sorted(k["hari"])
        if len(hari) < MIN_KALI:
            continue
        selang = [(b - a).days for a, b in zip(hari, hari[1:])]
        med = statistics.median(selang)
        if med < MIN_INTERVAL:
            continue
        simpangan = statistics.median([abs(i - med) for i in selang])
        if simpangan / med > MAX_KERAGAMAN:
            continue
        interval = int(round(med))
        berikutnya = hari[-1] + timedelta(days=interval)
        sisa = (berikutnya - today).days
        hasil.append({
            "kunci": "-".join(sorted(k["inti"])),
            "label": k["ket"].most_common(1)[0][0].capitalize(),
            "kali": len(hari),
            "interval_hari": interval,
            "rata_nominal": round(statistics.mean(k["hari"].values())),
            "terakhir": hari[-1].isoformat(),
            "berikutnya": berikutnya.isoformat(),
            "sisa_hari": sisa,
            "keyakinan": "tinggi" if len(hari) >= 5 and simpangan / med <= 0.15 else "sedang",
            "aktif": sisa >= -max(3, interval // 2),  # sudah lama lewat = kebiasaan mungkin berhenti
        })
    return sorted(hasil, key=lambda p: p["sisa_hari"])


def buat_pengingat_otomatis(conn, today=None, horizon=7):
    """Buat pengingat untuk pola yang jatuh temponya <= `horizon` hari. Tidak membuat duplikat."""
    today = today or date.today()
    dibuat = []
    for p in deteksi(conn, today):
        if not p["aktif"] or p["sisa_hari"] > horizon:
            continue
        kunci = f'{p["kunci"]}|{p["berikutnya"]}'
        if conn.execute("SELECT 1 FROM pola_log WHERE kunci=?", (kunci,)).fetchone():
            continue
        conn.execute("INSERT OR IGNORE INTO pola_log VALUES (?, ?)", (kunci, today.isoformat()))

        inti = set(p["kunci"].split("-"))
        target = date.fromisoformat(p["berikutnya"])
        sudah_ada = False
        for judul, tempo in conn.execute("SELECT judul, jatuh_tempo FROM pengingat WHERE status='AKTIF'").fetchall():
            d = _tgl(tempo)
            if d and abs((d - target).days) <= 10 and len(inti & tokens(judul)) / len(inti) >= 0.5:
                sudah_ada = True   # pengguna sudah punya pengingat serupa
                break
        if sudah_ada:
            continue
        judul = f"🔁 {p['label']} (biasanya tiap ±{p['interval_hari']} hari)"
        conn.execute("INSERT INTO pengingat (judul, jatuh_tempo) VALUES (?, ?)", (judul, p["berikutnya"]))
        dibuat.append({"judul": judul, "jatuh_tempo": p["berikutnya"]})
    return dibuat
