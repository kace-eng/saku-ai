import sqlite3
from datetime import date, datetime, timedelta

from core import config


def _siapkan(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DB", str(tmp_path / "a.db"))
    import notifier
    sent = []
    monkeypatch.setattr(notifier, "kirim", lambda judul, isi, nid: sent.append(judul) or True)
    c = sqlite3.connect(config.APP_DB)
    c.execute("CREATE TABLE pengingat (id INTEGER PRIMARY KEY AUTOINCREMENT, judul TEXT, jatuh_tempo TEXT, status TEXT DEFAULT 'AKTIF')")
    for j, d in [("H3", 3), ("Hari H", 0), ("Telat", -2), ("Jauh", 30)]:
        c.execute("INSERT INTO pengingat(judul,jatuh_tempo) VALUES (?,?)", ((j), (date.today() + timedelta(days=d)).isoformat()))
    c.commit(); c.close()
    return notifier, sent


def test_jadwal_dan_tanpa_dobel(tmp_path, monkeypatch):
    n, sent = _siapkan(tmp_path, monkeypatch)
    pagi = datetime.combine(date.today(), datetime.min.time()).replace(hour=9)
    assert n.cek_sekali(pagi.replace(hour=23)) == 0          # jam senyap
    assert n.cek_sekali(pagi) == 4                            # 3 pengingat + ringkasan
    assert not any("Jauh" in s for s in sent)
    assert n.cek_sekali(pagi.replace(minute=30)) == 0         # tidak dobel


def test_notifikasi_anggaran_dan_pola(tmp_path, monkeypatch):
    from datetime import timedelta
    n, sent = _siapkan(tmp_path, monkeypatch)
    c = sqlite3.connect(config.APP_DB)
    from core import indeks, skema
    skema.pastikan(c)
    indeks.atur_anggaran(c, "Makan", 100000)
    hari = date.today()
    c.execute("INSERT INTO pengeluaran (tanggal,kategori,keterangan,nominal) VALUES (?,?,?,?)", (hari.isoformat(), "Makan", "bakso", 90000))
    for h in (54, 36, 18):
        c.execute("INSERT INTO pengeluaran (tanggal,kategori,keterangan,nominal) VALUES (?,?,?,?)",
                  ((hari - timedelta(days=h)).isoformat(), "Belanja", "token listrik", 100000))
    c.commit(); c.close()
    pagi = datetime.combine(hari, datetime.min.time()).replace(hour=9)
    n.cek_sekali(pagi)
    assert any("Anggaran Makan" in s for s in sent)
    assert any("Pengingat otomatis" in s for s in sent)
    jumlah = len(sent)
    n.cek_sekali(pagi.replace(minute=30))
    assert len(sent) == jumlah                      # tidak ada pengiriman ulang
