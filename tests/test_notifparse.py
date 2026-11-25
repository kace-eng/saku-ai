import pytest

from core import notifparse


@pytest.mark.parametrize("judul,isi,jenis,nominal", [
    ("Pembayaran berhasil", "Kamu membayar Rp25.000 ke Indomaret. Saldo Rp1.200.000", "keluar", 25000),
    ("DANA", "Pembayaran berhasil Rp 18.500,00 di Warung Bu Sri pada 25 Nov", "keluar", 18500),
    ("Transfer masuk", "Rp3.000.000 dari BUDI SANTOSO. Saldo Rp4.200.000", "masuk", 3_000_000),
    ("m-Banking", "Transfer berhasil Rp150.000 ke SITI. Sisa saldo Rp900.000", "keluar", 150000),
])
def test_transaksi_dikenali(judul, isi, jenis, nominal):
    t = notifparse.baca(judul, isi)
    assert t and t["jenis"] == jenis and t["nominal"] == nominal


def test_saldo_tidak_pernah_dianggap_nominal():
    t = notifparse.baca("Pembayaran berhasil", "Saldo Rp1.200.000. Dibayar Rp25.000 ke Kopi Kenangan")
    assert t["nominal"] == 25000


def test_label_diambil_dari_tujuan():
    assert notifparse.baca("Pembayaran berhasil", "Rp25.000 ke Indomaret. Saldo Rp1.000.000")["label"] == "Indomaret"
    assert notifparse.baca("Uang masuk", "Rp500.000 dari Andi")["label"] == "Andi"


@pytest.mark.parametrize("judul,isi", [
    ("Kode OTP", "Kode OTP Anda 123456. Jangan beritahu siapa pun. Rp25.000"),
    ("Promo", "Diskon Rp50.000 untuk kamu! Belanja sekarang"),
    ("Pembayaran gagal", "Pembayaran Rp25.000 gagal, saldo tidak cukup"),
    ("Top up berhasil", "Top up Rp100.000 berhasil"),
    ("Tagihan", "Tagihan listrik Rp200.000 akan jatuh tempo besok"),
    ("Halo", "Selamat datang kembali!"),
    ("Cashback", "Selamat! Kamu menerima cashback Rp5.000"),
])
def test_bukan_transaksi_diabaikan(judul, isi):
    assert notifparse.baca(judul, isi) is None


def test_pembayaran_dengan_promo_tetap_dicatat():
    t = notifparse.baca("Pembayaran berhasil", "Rp25.000 ke Indomaret. Kamu dapat cashback Rp500!")
    assert t and t["nominal"] == 25000
