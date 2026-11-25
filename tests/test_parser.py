from datetime import date

from core import parser


def test_pengeluaran_dan_pengingat():
    h = parser.parse("Ganti oli 65rb, ingatkan servis 2 bulan lagi", date(2026, 11, 25))
    assert h["pengeluaran"][0]["nominal"] == 65000
    assert h["pengeluaran"][0]["kategori"] == "Servis"
    assert h["pengingat"][0]["jatuh_tempo"] == "2027-01-25"


def test_format_rupiah_dan_catatan():
    h = parser.parse("makan siang Rp 25.000, ide bikin kanal video", date(2026, 11, 25))
    assert h["pengeluaran"][0]["nominal"] == 25000
    assert h["catatan"] == ["ide bikin kanal video"]


def test_akhir_bulan():
    assert parser.tambah_bulan(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_pemasukan_dikenali():
    h = parser.parse("gaji masuk 3jt, makan siang 25rb", date(2026, 11, 25))
    assert h["pemasukan"][0]["nominal"] == 3_000_000
    assert [p["nominal"] for p in h["pengeluaran"]] == [25000]


def test_bayar_gaji_adalah_pengeluaran_bukan_pemasukan():
    h = parser.parse("bayar gaji karyawan 2jt", date(2026, 11, 25))
    assert h["pemasukan"] == [] and h["pengeluaran"][0]["nominal"] == 2_000_000


def test_bonus_dan_transfer_masuk():
    h = parser.parse("dapat bonus 500rb dan transfer masuk 1,5jt", date(2026, 11, 25))
    assert sorted(p["nominal"] for p in h["pemasukan"]) == [500000, 1_500_000]


def test_koma_desimal_tidak_memotong_angka():
    h = parser.parse("servis motor 1,5jt, makan 20rb", date(2026, 11, 25))
    assert [p["nominal"] for p in h["pengeluaran"]] == [1_500_000, 20000]
