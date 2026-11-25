import sqlite3
from datetime import datetime

import pytest

from core import config


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DB", str(tmp_path / "a.db"))
    monkeypatch.setattr(config, "LEDGER_DB", str(tmp_path / "l.db"))
    import notifier
    import penangkap
    terkirim = []
    monkeypatch.setattr(notifier, "kirim", lambda judul, isi, nid, batal_url=None: terkirim.append((judul, isi, batal_url)) or True)
    return penangkap, terkirim


SIANG = datetime(2026, 11, 25, 13, 0)


def _notif(judul, isi, pkg="id.dana", key="k1", when=1):
    return {"packageName": pkg, "title": judul, "content": isi, "key": key, "when": when}


def test_catat_keluar_masuk_dan_tombol_batal(env):
    p, terkirim = env
    hasil = p.proses([_notif("Pembayaran berhasil", "Rp25.000 ke Indomaret", key="a"),
                      _notif("Transfer masuk", "Rp3.000.000 dari Budi", key="b")], {"id.dana"}, SIANG)
    assert [h["jenis"] for h in hasil] == ["keluar", "masuk"]
    c = sqlite3.connect(config.APP_DB)
    assert c.execute("SELECT keterangan, nominal FROM pengeluaran").fetchall() == [("🤖 Indomaret", 25000.0)]
    assert c.execute("SELECT nominal FROM pemasukan").fetchall() == [(3_000_000.0,)]
    assert len(terkirim) == 2 and "/hapus-pengeluaran/" in terkirim[0][2]


def test_tidak_dobel_dan_paket_lain_diabaikan(env):
    p, _ = env
    n = _notif("Pembayaran berhasil", "Rp25.000 ke Indomaret")
    assert len(p.proses([n], {"id.dana"}, SIANG)) == 1
    assert p.proses([n], {"id.dana"}, SIANG) == []                                   # persis sama
    assert p.proses([{**n, "when": 999, "key": "baru"}], {"id.dana"}, SIANG) == []   # dikirim ulang aplikasi
    assert p.proses([_notif("Pembayaran berhasil", "Rp9.000 ke X", pkg="com.lain")], {"id.dana"}, SIANG) == []


def test_otp_dan_promo_tidak_dicatat(env):
    p, _ = env
    assert p.proses([_notif("OTP", "Kode OTP 123456 Rp1.000"), _notif("Promo", "Diskon Rp50.000")], {"id.dana"}, SIANG) == []


def test_privasi_nomor_rekening_disensor(env):
    p, _ = env
    p.proses([_notif("Transfer berhasil", "Rp150.000 ke 1234567890123")], {"id.dana"}, SIANG)
    ket = sqlite3.connect(config.APP_DB).execute("SELECT keterangan FROM pengeluaran").fetchone()[0]
    assert "1234567890123" not in ket


def test_jam_senyap_tetap_mencatat_tanpa_notifikasi(env):
    p, terkirim = env
    malam = datetime(2026, 11, 25, 23, 30)
    assert len(p.proses([_notif("Pembayaran berhasil", "Rp25.000 ke Indomaret")], {"id.dana"}, malam)) == 1
    assert terkirim == []
