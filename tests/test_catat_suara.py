import catat_suara
import notifier


class _Res:
    def __init__(self, kode, data):
        self.status_code, self._d = kode, data

    def json(self):
        return self._d


def test_ringkasan_dan_notifikasi(monkeypatch):
    kirim = []
    monkeypatch.setattr(notifier, "kirim", lambda j, i, n, batal_url=None: kirim.append((j, i)))
    data = {"hasil": {"pengeluaran": [{"nominal": 30000, "keterangan": "bensin"}], "pemasukan": [], "pengingat": [], "catatan": []},
            "peringatan": [{"kategori": "Transport", "persen": 90}]}
    monkeypatch.setattr(catat_suara.requests, "post", lambda *a, **k: _Res(200, data))
    assert catat_suara.jalankan("bensin 30rb") == 0
    assert kirim[0][0] == "✔ Tercatat" and "Rp 30.000" in kirim[0][1] and "Transport 90%" in kirim[0][1]


def test_server_mati_dan_tidak_terdengar(monkeypatch):
    kirim = []
    monkeypatch.setattr(notifier, "kirim", lambda j, i, n, batal_url=None: kirim.append(j))

    def mati(*a, **k):
        raise catat_suara.requests.exceptions.ConnectionError()
    monkeypatch.setattr(catat_suara.requests, "post", mati)
    assert catat_suara.jalankan("halo") == 1 and "belum jalan" in kirim[0]
    assert catat_suara.jalankan("") == 1
