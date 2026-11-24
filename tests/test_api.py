import json


def test_catat_lokal_tanpa_ai(app_ctx):
    _, c = app_ctx
    r = c.post("/catat-pintar", json={"teks": "Ganti oli 65rb, ingatkan servis 2 bulan lagi"})
    assert r.status_code == 200 and r.json["mode"] == "lokal"
    d = c.get("/dashboard-data").json
    assert d["total_pengeluaran"] == 65000 and len(d["pengingat"]) == 1


def test_input_kosong_dan_foto_tanpa_ai(app_ctx):
    _, c = app_ctx
    assert c.post("/catat-pintar", json={"teks": ""}).status_code == 400
    assert c.post("/catat-pintar", json={"image_base64": "AAAA"}).status_code == 502


def test_foto_ai_dan_anti_duplikat(app_ctx):
    m, c = app_ctx
    fake = json.dumps({"pengeluaran": [{"kategori": "Makan", "keterangan": "nasi", "nominal": "Rp 25.000"}],
                       "pengingat": [{"judul": "Listrik", "jatuh_tempo": "ngawur"}],
                       "catatan": [], "saran_singkat": "Hemat!"})
    m.generate = lambda parts, json_mode=False, timeout=40: "```json\n" + fake + "\n```"
    body = {"image_base64": "AAAA", "mime_type": "image/jpeg"}
    r = c.post("/catat-pintar", json=body)
    assert r.status_code == 200 and r.json["hasil"]["pengeluaran"][0]["nominal"] == 25000
    assert c.post("/catat-pintar", json=body).status_code == 409


def test_hapus_csv_verifikasi_dan_path_traversal(app_ctx):
    _, c = app_ctx
    c.post("/catat-pintar", json={"teks": "kopi 15rb"})
    eid = c.get("/dashboard-data").json["pengeluaran"][0]["id"]
    assert "kopi" in c.get("/export-csv").data.decode()
    assert c.post(f"/hapus-pengeluaran/{eid}").json["status"] == "OK"
    assert c.get("/dashboard-data").json["total_pengeluaran"] == 0
    assert c.get("/verifikasi").json["hasil"].startswith("AMAN")
    assert c.get("/../core/config.py").status_code == 404
