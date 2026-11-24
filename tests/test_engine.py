from core.engine import SovereignEngine


def test_sensor_privasi(tmp_path):
    e = SovereignEngine(str(tmp_path / "l.db"))
    out = e.sanitize_privacy("hub 081234567890 a@b.com rek 123456789012")
    assert "081234567890" not in out and "a@b.com" not in out and "123456789012" not in out


def test_ledger_utuh_dan_terdeteksi_rusak(tmp_path):
    import sqlite3
    e = SovereignEngine(str(tmp_path / "l.db"))
    e.record_decision("t", "catatan", [42500, 18750, 93000, 15200])
    assert e.verify_ok()
    with sqlite3.connect(e.db_path) as c:
        c.execute("UPDATE audit_ledger SET clean_context='diubah' WHERE block_index=1")
    assert not e.verify_ok()
