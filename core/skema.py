"""Skema database aplikasi (idempoten, aman dipanggil berkali-kali dari proses mana pun)."""

TABEL = [
    """CREATE TABLE IF NOT EXISTS pengeluaran (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tanggal TEXT, kategori TEXT,
        keterangan TEXT, nominal REAL, bukti_hash TEXT)""",
    """CREATE TABLE IF NOT EXISTS pengingat (
        id INTEGER PRIMARY KEY AUTOINCREMENT, judul TEXT, jatuh_tempo TEXT,
        status TEXT DEFAULT 'AKTIF')""",
    """CREATE TABLE IF NOT EXISTS catatan (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tanggal TEXT, isi TEXT)""",
    """CREATE TABLE IF NOT EXISTS pemasukan (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tanggal TEXT, sumber TEXT, nominal REAL)""",
    "CREATE TABLE IF NOT EXISTS pengaturan (kunci TEXT PRIMARY KEY, nilai TEXT)",
    "CREATE TABLE IF NOT EXISTS anggaran (kategori TEXT PRIMARY KEY COLLATE NOCASE, batas REAL)",
    "CREATE TABLE IF NOT EXISTS pola_log (kunci TEXT PRIMARY KEY, dibuat_pada TEXT)",
    "CREATE TABLE IF NOT EXISTS notif_log (kunci TEXT PRIMARY KEY, dikirim_pada TEXT)",
]


def pastikan(conn):
    for sql in TABEL:
        conn.execute(sql)
