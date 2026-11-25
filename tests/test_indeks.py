import sqlite3
from datetime import date, timedelta

from core import indeks, skema

HARI_INI = date(2026, 11, 25)


def _db():
    c = sqlite3.connect(":memory:")
    skema.pastikan(c)
    return c


def _keluar(c, hari_lalu, nominal, kategori="Makan"):
    c.execute("INSERT INTO pengeluaran (tanggal, kategori, keterangan, nominal) VALUES (?,?,?,?)",
              ((HARI_INI - timedelta(days=hari_lalu)).isoformat(), kategori, "x", nominal))


def test_runway_dan_level():
    c = _db()
    for h in range(0, 10):
        _keluar(c, h, 50000)                       # rata-rata 50rb/hari
    indeks.atur(c, saldo=1_500_000, today=HARI_INI)
    d = indeks.hitung(c, HARI_INI)
    assert d["rata_harian"] == 50000 and d["runway_hari"] == 30 and d["level"] == "Waspada"


def test_pengeluaran_baru_mengurangi_saldo():
    c = _db()
    _keluar(c, 1, 50000)
    indeks.atur(c, saldo=1_000_000, today=HARI_INI)
    _keluar(c, 0, 200000)                           # dicatat setelah saldo diatur
    assert indeks.hitung(c, HARI_INI)["saldo"] == 800000


def test_tanpa_saldo_atau_tanpa_data_runway_kosong():
    c = _db()
    assert indeks.hitung(c, HARI_INI)["runway_hari"] is None
    _keluar(c, 0, 10000)
    assert indeks.hitung(c, HARI_INI)["runway_hari"] is None   # saldo belum diisi


def test_saldo_habis_level_rawan():
    c = _db()
    _keluar(c, 0, 100000)
    indeks.atur(c, saldo=50000, today=HARI_INI)
    _keluar(c, 0, 100000)
    d = indeks.hitung(c, HARI_INI)
    assert d["runway_hari"] == 0 and d["level"] == "Rawan"


def test_tren_bulanan_dan_tabungan():
    c = _db()
    _keluar(c, 40, 1_000_000)                        # Oktober
    for h in (0, 1, 2):
        _keluar(c, h, 100000)                        # 3 hari di November -> proyeksi 100rb*30 = 3jt
    indeks.atur(c, pemasukan=4_000_000, today=HARI_INI)
    d = indeks.hitung(c, HARI_INI)
    assert d["bulan_ini"] == 300000 and d["proyeksi_bulan"] == int(300000 / 25 * 30)
    assert d["tren_persen"] is not None and d["rasio_tabungan"] is not None


def test_anggaran_status_dan_hapus():
    c = _db()
    indeks.atur_anggaran(c, "Makan", 100000)
    indeks.atur_anggaran(c, "TOTAL", 1_000_000)
    _keluar(c, 0, 85000, "Makan")
    st = {a["kategori"]: a for a in indeks.status_anggaran(c, HARI_INI)}
    assert st["Makan"]["status"] == "hampir" and st["TOTAL"]["status"] == "aman"
    _keluar(c, 0, 20000, "makan")                    # huruf kecil tetap terhitung
    st = {a["kategori"]: a for a in indeks.status_anggaran(c, HARI_INI)}
    assert st["Makan"]["status"] == "lewat" and st["Makan"]["pakai"] == 105000
    indeks.atur_anggaran(c, "Makan", 0)
    assert [a["kategori"] for a in indeks.status_anggaran(c, HARI_INI)] == ["TOTAL"]


def test_pemasukan_menambah_saldo_dan_dipakai_untuk_rasio():
    c = _db()
    indeks.atur(c, saldo=1_000_000, today=HARI_INI)
    c.execute("INSERT INTO pemasukan (tanggal, sumber, nominal) VALUES (?,?,?)", (HARI_INI.isoformat(), "Gaji", 3_000_000))
    _keluar(c, 0, 100000)
    d = indeks.hitung(c, HARI_INI)
    assert d["saldo"] == 3_900_000 and d["pemasukan_bulan_ini"] == 3_000_000
    assert d["rasio_tabungan"] is not None and d["rasio_tabungan"] > 0


def test_pemasukan_lama_sebelum_saldo_diatur_tidak_dihitung_dua_kali():
    c = _db()
    c.execute("INSERT INTO pemasukan (tanggal, sumber, nominal) VALUES (?,?,?)", (HARI_INI.isoformat(), "Gaji", 3_000_000))
    indeks.atur(c, saldo=3_000_000, today=HARI_INI)     # saldo sudah termasuk gaji tadi
    assert indeks.hitung(c, HARI_INI)["saldo"] == 3_000_000
