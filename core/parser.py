"""Parser lokal (tanpa AI) sebagai cadangan saat Gemini tidak tersedia."""
import calendar
import re
from datetime import date, timedelta

UNIT = {"rb": 1_000, "ribu": 1_000, "k": 1_000, "jt": 1_000_000, "juta": 1_000_000}
AMOUNT_RE = re.compile(
    r"(?:rp\.?\s*)?(\d{1,3}(?:\.\d{3})+|\d+(?:[.,]\d+)?)\s*(rb|ribu|jt|juta|k)?\b", re.I)
WAKTU_RE = re.compile(r"(\d+)\s*(hari|minggu|bulan)\s*lagi", re.I)
MASUK_RE = re.compile(
    r"\b(gaji|gajian|honor|bonus|thr|komisi|pemasukan|pendapatan|uang saku|(?:uang|transfer|dana|saldo) masuk|cair|"
    r"terima (?:uang|gaji|transfer)|dapat (?:uang|gaji|transfer)|dikirimi|dikasih (?:uang|duit))\b", re.I)
KELUAR_RE = re.compile(r"\b(bayar|beli|belanja|ganti|servis|isi)\b", re.I)
REMIND_RE = re.compile(r"\b(ingatkan|ingetin|pengingat|reminder|jadwalkan)\b", re.I)

KATEGORI = {
    "Transport": ["bensin", "pertamax", "pertalite", "parkir", "tol", "ojek", "grab", "gojek", "bus", "kereta", "angkot"],
    "Makan": ["makan", "minum", "kopi", "bakso", "nasi", "ayam", "sate", "mie", "sarapan", "jajan", "snack"],
    "Servis": ["servis", "service", "oli", "ban", "tambal", "bengkel", "aki"],
    "Belanja": ["beli", "belanja", "indomaret", "alfamart", "pulsa", "token", "listrik", "paket"],
}


def tambah_bulan(d: date, n: int) -> date:
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _nominal(klausa: str):
    """Kembalikan (nominal, span) pertama yang jelas berupa uang, atau (None, None)."""
    for m in AMOUNT_RE.finditer(klausa):
        raw, unit = m.group(1), (m.group(2) or "").lower()
        # abaikan angka yang bagian dari "2 bulan lagi" dsb.
        if re.match(r"\s*(hari|minggu|bulan|tahun|kali|jam|menit)\b", klausa[m.end():], re.I) and not unit:
            continue
        if unit:
            val = float(raw.replace(".", "").replace(",", ".")) if "," in raw else float(raw)
            return val * UNIT[unit], m.span()
        if "." in raw and re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
            return float(raw.replace(".", "")), m.span()
        if raw.isdigit() and int(raw) >= 1000:
            return float(raw), m.span()
    return None, None


def _kategori(teks: str) -> str:
    t = teks.lower()
    for kat, kata in KATEGORI.items():
        if any(k in t for k in kata):
            return kat
    return "Lainnya"


def parse(teks: str, hari_ini: date = None) -> dict:
    hari_ini = hari_ini or date.today()
    hasil = {"pengeluaran": [], "pemasukan": [], "pengingat": [], "catatan": [], "saran_singkat": ""}
    for klausa in re.split(r"(?<!\d),|,(?!\d)|[;\n]|\bdan\b|\blalu\b|\bterus\b", teks):  # koma desimal (1,5jt) tidak memotong
        klausa = klausa.strip(" .")
        if not klausa:
            continue
        nominal, span = _nominal(klausa)
        waktu = WAKTU_RE.search(klausa)
        ingat = REMIND_RE.search(klausa)

        masuk = bool(nominal and MASUK_RE.search(klausa) and not KELUAR_RE.search(klausa))
        if masuk:
            sumber = (klausa[:span[0]] + klausa[span[1]:]).strip(" -:") or "Pemasukan"
            hasil["pemasukan"].append({"sumber": sumber.capitalize(), "nominal": nominal})
        elif nominal and not (ingat and waktu):
            ket = (klausa[:span[0]] + klausa[span[1]:]).strip(" -:") or klausa
            hasil["pengeluaran"].append({"kategori": _kategori(klausa), "keterangan": ket, "nominal": nominal})
        if ingat or waktu:
            n, satuan = (int(waktu.group(1)), waktu.group(2).lower()) if waktu else (0, "hari")
            if satuan == "hari":
                due = hari_ini + timedelta(days=n)
            elif satuan == "minggu":
                due = hari_ini + timedelta(weeks=n)
            else:
                due = tambah_bulan(hari_ini, n)
            judul = REMIND_RE.sub("", WAKTU_RE.sub("", klausa)).strip(" -:") or klausa
            hasil["pengingat"].append({"judul": judul, "jatuh_tempo": due.isoformat()})
        elif not nominal:
            hasil["catatan"].append(klausa)
    hasil["saran_singkat"] = "Tersimpan lewat parser lokal (AI sedang tidak tersedia)."
    return hasil
