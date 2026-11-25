"""Indeks Kemandirian (sisa hari bertahan, tren) dan batas anggaran per kategori."""
import calendar
from datetime import date, timedelta

LEVEL = [(30, "Rawan"), (90, "Waspada"), (180, "Cukup")]  # di atas 180 hari = "Kuat"
AMBANG_HAMPIR = 80.0


def _get(conn, k):
    r = conn.execute("SELECT nilai FROM pengaturan WHERE kunci=?", (k,)).fetchone()
    return r[0] if r else None


def _set(conn, k, v):
    conn.execute("INSERT INTO pengaturan(kunci, nilai) VALUES (?, ?) "
                 "ON CONFLICT(kunci) DO UPDATE SET nilai=excluded.nilai", (k, str(v)))


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def atur(conn, saldo=None, pemasukan=None, today=None):
    """Saldo dicatat bersama 'titik acuan' pengeluaran, sehingga pengeluaran berikutnya otomatis mengurangi saldo."""
    today = today or date.today()
    if saldo is not None:
        basis = conn.execute("SELECT COALESCE(MAX(id), 0) FROM pengeluaran").fetchone()[0]
        _set(conn, "saldo_awal", saldo)
        _set(conn, "saldo_basis_id", basis)
        _set(conn, "saldo_basis_masuk", conn.execute("SELECT COALESCE(MAX(id), 0) FROM pemasukan").fetchone()[0])
        _set(conn, "saldo_tanggal", today.isoformat())
    if pemasukan is not None:
        _set(conn, "pemasukan", pemasukan)


def atur_anggaran(conn, kategori, batas):
    if batas <= 0:
        conn.execute("DELETE FROM anggaran WHERE kategori=?", (kategori,))
    else:
        conn.execute("INSERT INTO anggaran(kategori, batas) VALUES (?, ?) "
                     "ON CONFLICT(kategori) DO UPDATE SET batas=excluded.batas", (kategori, batas))


def _total_bulan(conn, prefix, kategori=None):
    if kategori and kategori.upper() != "TOTAL":
        q, a = "SELECT COALESCE(SUM(nominal),0) FROM pengeluaran WHERE tanggal LIKE ? AND LOWER(kategori)=LOWER(?)", (prefix + "%", kategori)
    else:
        q, a = "SELECT COALESCE(SUM(nominal),0) FROM pengeluaran WHERE tanggal LIKE ?", (prefix + "%",)
    return float(conn.execute(q, a).fetchone()[0])


def status_anggaran(conn, today=None):
    today = today or date.today()
    prefix = today.strftime("%Y-%m")
    out = []
    for kategori, batas in conn.execute("SELECT kategori, batas FROM anggaran ORDER BY kategori").fetchall():
        pakai = _total_bulan(conn, prefix, kategori)
        persen = pakai / batas * 100 if batas else 0.0
        out.append({"kategori": kategori, "batas": batas, "pakai": pakai, "persen": round(persen, 1),
                    "sisa": batas - pakai,
                    "status": "lewat" if persen >= 100 else ("hampir" if persen >= AMBANG_HAMPIR else "aman")})
    return out


def hitung(conn, today=None):
    today = today or date.today()
    saldo_awal = _num(_get(conn, "saldo_awal"))
    pemasukan = _num(_get(conn, "pemasukan"))

    # --- sisa dana & runway
    saldo_kini = None
    if saldo_awal is not None:
        basis = int(_num(_get(conn, "saldo_basis_id")) or 0)
        keluar = conn.execute("SELECT COALESCE(SUM(nominal),0) FROM pengeluaran WHERE id > ?", (basis,)).fetchone()[0]
        basis_masuk = int(_num(_get(conn, "saldo_basis_masuk")) or 0)
        masuk = conn.execute("SELECT COALESCE(SUM(nominal),0) FROM pemasukan WHERE id > ?", (basis_masuk,)).fetchone()[0]
        saldo_kini = saldo_awal - float(keluar) + float(masuk)

    pertama = conn.execute("SELECT MIN(tanggal) FROM pengeluaran").fetchone()[0]
    hari_data, rata_harian = 0, 0.0
    if pertama:
        try:
            hari_data = (today - date.fromisoformat(pertama)).days + 1
        except ValueError:
            hari_data = 0
    if hari_data > 0:
        jendela = min(30, hari_data)
        mulai = (today - timedelta(days=jendela - 1)).isoformat()
        total = conn.execute("SELECT COALESCE(SUM(nominal),0) FROM pengeluaran WHERE tanggal >= ?", (mulai,)).fetchone()[0]
        rata_harian = float(total) / jendela

    runway, level = None, None
    if saldo_kini is not None and rata_harian > 0:
        runway = 0 if saldo_kini <= 0 else int(saldo_kini / rata_harian)
        level = next((nama for batas, nama in LEVEL if runway < batas), "Kuat")

    # --- tren bulanan
    prefix = today.strftime("%Y-%m")
    bulan_lalu_prefix = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    bulan_ini = _total_bulan(conn, prefix)
    bulan_lalu = _total_bulan(conn, bulan_lalu_prefix)
    hari_bulan = calendar.monthrange(today.year, today.month)[1]
    proyeksi = bulan_ini / today.day * hari_bulan if today.day >= 3 else bulan_ini
    tren = round((proyeksi - bulan_lalu) / bulan_lalu * 100, 1) if bulan_lalu > 0 else None
    masuk_bulan = float(conn.execute("SELECT COALESCE(SUM(nominal),0) FROM pemasukan WHERE tanggal LIKE ?",
                                     (prefix + "%",)).fetchone()[0])
    dasar = masuk_bulan if masuk_bulan > 0 else pemasukan   # pemasukan nyata didahulukan dari perkiraan
    rasio = round((dasar - proyeksi) / dasar * 100, 1) if dasar and dasar > 0 else None

    return {
        "saldo": saldo_kini, "saldo_awal": saldo_awal, "pemasukan": pemasukan, "pemasukan_bulan_ini": masuk_bulan,
        "rata_harian": round(rata_harian), "hari_data": hari_data, "data_cukup": hari_data >= 7,
        "runway_hari": runway, "level": level,
        "bulan_ini": bulan_ini, "bulan_lalu": bulan_lalu, "proyeksi_bulan": round(proyeksi),
        "tren_persen": tren, "rasio_tabungan": rasio,
        "anggaran": status_anggaran(conn, today),
    }
