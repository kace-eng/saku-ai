import sqlite3
from datetime import date, timedelta

from core import pola, skema

HARI_INI = date(2026, 11, 25)


def _db():
    c = sqlite3.connect(":memory:")
    skema.pastikan(c)
    return c


def _isi(c, ket, hari_lalu, nominal=65000, kategori="Servis"):
    for h in hari_lalu:
        c.execute("INSERT INTO pengeluaran (tanggal, kategori, keterangan, nominal) VALUES (?,?,?,?)",
                  ((HARI_INI - timedelta(days=h)).isoformat(), kategori, ket, nominal))


def test_pola_oli_terdeteksi_dengan_variasi_kata():
    c = _db()
    _isi(c, "Ganti oli", [185, 125])
    _isi(c, "oli motor", [64])
    _isi(c, "Ganti oli", [5])
    p = pola.deteksi(c, HARI_INI)
    assert len(p) == 1
    assert p[0]["kali"] == 4 and 58 <= p[0]["interval_hari"] <= 62
    assert p[0]["berikutnya"] == (HARI_INI - timedelta(days=5) + timedelta(days=p[0]["interval_hari"])).isoformat()


def test_tidak_teratur_atau_terlalu_sedikit_bukan_pola():
    c = _db()
    _isi(c, "servis ac", [100, 90, 20])          # selang 10 & 70: tidak konsisten
    _isi(c, "ganti ban", [60, 5])                # baru 2 kali
    _isi(c, "kopi", list(range(1, 10)), 8000, "Makan")  # harian -> bukan pola
    assert pola.deteksi(c, HARI_INI) == []


def test_pengingat_otomatis_tanpa_duplikat():
    c = _db()
    _isi(c, "token listrik", [54, 36, 18], 100000, "Belanja")   # tiap 18 hari -> berikutnya hari ini
    dibuat = pola.buat_pengingat_otomatis(c, HARI_INI)
    assert len(dibuat) == 1 and dibuat[0]["jatuh_tempo"] == HARI_INI.isoformat()
    assert pola.buat_pengingat_otomatis(c, HARI_INI) == []       # panggilan ulang tidak menggandakan
    assert c.execute("SELECT COUNT(*) FROM pengingat").fetchone()[0] == 1


def test_tidak_membuat_jika_pengguna_sudah_punya_pengingat_serupa():
    c = _db()
    _isi(c, "token listrik", [54, 36, 18], 100000, "Belanja")
    c.execute("INSERT INTO pengingat (judul, jatuh_tempo) VALUES (?, ?)",
              ("Beli token listrik", (HARI_INI + timedelta(days=2)).isoformat()))
    assert pola.buat_pengingat_otomatis(c, HARI_INI) == []


def test_jauh_di_depan_belum_dibuat_dan_yang_lama_berhenti_diabaikan():
    c = _db()
    _isi(c, "ganti oli", [185, 125, 65, 5])      # berikutnya 55 hari lagi
    assert pola.buat_pengingat_otomatis(c, HARI_INI) == []
    c2 = _db()
    _isi(c2, "pajak stnk", [500, 400, 300, 200], 300000)  # terakhir 200 hari lalu, selang 100 -> sudah lewat jauh
    assert pola.deteksi(c2, HARI_INI)[0]["aktif"] is False
    assert pola.buat_pengingat_otomatis(c2, HARI_INI) == []
