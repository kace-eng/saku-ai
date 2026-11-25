"""Membaca notifikasi bank/e-wallet menjadi transaksi. Murni lokal (regex), tidak dikirim ke AI."""
import re

RP_RE = re.compile(r"(?:rp\.?|idr)\s?(\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,2})?", re.I)

HARD_SKIP = re.compile(r"\b(otp|kode verifikasi|kode rahasia|jangan (?:beritahu|bagikan)|gagal|dibatalkan|kedaluwarsa|"
                       r"jatuh tempo|top.?up|isi saldo|tarik tunai|menunggu pembayaran)\b", re.I)
PROMO = re.compile(r"\b(diskon|promo|voucher|cashback|potongan|hemat|gratis|klaim|kupon)\b", re.I)
KUAT_MASUK = re.compile(r"\b(uang masuk|transfer masuk|dana masuk|gaji|(?:menerima|terima|diterima) (?:transfer|dana|uang)|"
                        r"saldo bertambah|pengembalian dana)\b", re.I)
KUAT_KELUAR = re.compile(r"\b(pembayaran berhasil|berhasil membayar|transfer berhasil|pembelian berhasil|"
                         r"(?:kamu|anda) (?:telah )?membayar|debit|pembayaran)\b", re.I)
LABEL_RE = {
    "keluar": re.compile(r"\b(?:ke|di|kepada|untuk|merchant)\s+([A-Za-z0-9][\w .&'-]{2,30})", re.I),
    "masuk": re.compile(r"\bdari\s+([A-Za-z0-9][\w .&'-]{2,30})", re.I),
}
POTONG = re.compile(r"[.,;\n]| saldo| sebesar| pada | dengan | via | senilai | tanggal ", re.I)


def _nominal(teks):
    """Nominal pertama yang bukan 'saldo ...'."""
    for m in RP_RE.finditer(teks):
        sebelum = teks[max(0, m.start() - 14):m.start()].lower()
        if "saldo" in sebelum or "sisa" in sebelum:
            continue
        return float(m.group(1).replace(".", ""))
    return None


def baca(judul, isi):
    """Kembalikan {'jenis': 'keluar'|'masuk', 'nominal': float, 'label': str} atau None bila bukan transaksi jelas."""
    teks = f"{judul or ''}. {isi or ''}".strip()
    if HARD_SKIP.search(teks):
        return None
    nominal = _nominal(teks)
    if not nominal or nominal <= 0:
        return None
    if KUAT_MASUK.search(teks):
        jenis = "masuk"
    elif KUAT_KELUAR.search(teks):
        jenis = "keluar"
    else:
        return None
    if PROMO.search(teks) and not (KUAT_MASUK.search(teks) if jenis == "masuk"
                                   else re.search(r"pembayaran berhasil|berhasil membayar|transfer berhasil|pembelian berhasil", teks, re.I)):
        return None
    m = LABEL_RE[jenis].search(teks)
    label = POTONG.split(m.group(1))[0].strip() if m else ""
    return {"jenis": jenis, "nominal": nominal, "label": (label or (judul or "Transaksi"))[:40].strip()}
