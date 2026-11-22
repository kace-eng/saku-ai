import sys, os, base64, requests, sqlite3, csv, io, json, re, hashlib
from datetime import datetime, date
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, request, jsonify, send_from_directory, Response
from core.engine import SovereignEngine

def load_env():
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    if os.path.exists(env_path):
        for line in open(env_path):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k] = v

load_env()
app = Flask(__name__)
engine = SovereignEngine()
DB_PATH = "database/asisten_pribadi.db"
WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'web'))

def init_personal_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS pengeluaran (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tanggal TEXT, kategori TEXT, keterangan TEXT, nominal REAL, bukti_hash TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS pengingat (
            id INTEGER PRIMARY KEY AUTOINCREMENT, judul TEXT, jatuh_tempo TEXT, status TEXT DEFAULT 'AKTIF')""")
        conn.execute("""CREATE TABLE IF NOT EXISTS catatan (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tanggal TEXT, isi TEXT)""")

init_personal_db()

@app.route("/", methods=["GET"])
def home():
    return send_from_directory(WEB_DIR, "index.html")
@app.route("/<path:filename>")
def static_web(filename): return send_from_directory(WEB_DIR, filename)

@app.route("/dashboard-data", methods=["GET"])
def get_dashboard():
    with sqlite3.connect(DB_PATH) as conn:
        expenses = conn.execute("SELECT id, tanggal, kategori, keterangan, nominal FROM pengeluaran ORDER BY id DESC LIMIT 30").fetchall()
        reminders = conn.execute("SELECT id, judul, jatuh_tempo, status FROM pengingat WHERE status='AKTIF' ORDER BY jatuh_tempo ASC").fetchall()
        notes = conn.execute("SELECT id, tanggal, isi FROM catatan ORDER BY id DESC LIMIT 30").fetchall()
        total_keluar = conn.execute("SELECT COALESCE(SUM(nominal), 0) FROM pengeluaran").fetchone()[0]

    today = date.today()
    list_pengingat = []
    for r in reminders:
        try:
            due = datetime.strptime(r[2], "%Y-%m-%d").date()
            sisa_hari = (due - today).days
        except:
            sisa_hari = 99
        list_pengingat.append({"id": r[0], "judul": r[1], "jatuh_tempo": r[2], "sisa_hari": sisa_hari})

    list_pengeluaran = [{"id": e[0], "tanggal": e[1], "kategori": e[2], "keterangan": e[3], "nominal": e[4]} for e in expenses]
    list_catatan = [{"id": n[0], "tanggal": n[1], "isi": n[2]} for n in notes]
    return jsonify({"total_pengeluaran": total_keluar, "pengeluaran": list_pengeluaran, "pengingat": list_pengingat, "catatan": list_catatan})

@app.route("/catat-pintar", methods=["POST"])
def catat_pintar():
    data = request.get_json(silent=True) or {}
    teks_mentah = data.get("teks", "").strip()
    img_b64 = data.get("image_base64", "").strip()
    mime_type = data.get("mime_type", "image/jpeg")

    if not teks_mentah and not img_b64:
        return jsonify({"status": "ERROR", "pesan": "Ketik catatan atau pilih foto nota terlebih dahulu."})

    bukti_hash = ""
    if img_b64:
        bukti_hash = hashlib.sha256(img_b64.encode("utf-8")).hexdigest()
        with sqlite3.connect(DB_PATH) as conn:
            cek = conn.execute("SELECT id FROM pengeluaran WHERE bukti_hash=?", (bukti_hash,)).fetchone()
            if cek:
                return jsonify({"status": "ERROR", "pesan": "GUARDRAIL: Foto nota ini sudah pernah dicatat sebelumnya!"})

    teks_aman = engine.sanitize_privacy(teks_mentah) if teks_mentah else "Upload file atau foto nota"
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    hari_ini = date.today().strftime("%Y-%m-%d")

    prompt = f"""Hari ini {hari_ini}. Ekstrak teks/foto berikut menjadi JSON murni tanpa markdown:
{{"pengeluaran": [{{"kategori": "Transport/Makan/Servis/Belanja/Lainnya", "keterangan": "item", "nominal": 0}}], "pengingat": [{{"judul": "jadwal servis/tagihan", "jatuh_tempo": "YYYY-MM-DD"}}], "catatan": ["memo/ide/daftar belanja tanpa nominal uang & tanpa tanggal"], "saran_singkat": "1 kalimat komentar ramah"}}
Isi list kosong [] untuk bagian yang tidak relevan. Teks: "{teks_aman}" """

    parts = [{"text": prompt}]
    if img_b64:
        parts.append({"inline_data": {"mime_type": mime_type, "data": img_b64}})

    b64_endpoint = "aHR0cHM6Ly9nZW5lcmF0aXZlbGFuZ3VhZ2UuZ29vZ2xlYXBpcy5jb20vdjFiZXRhL21vZGVscy9nZW1pbmktMy41LWZsYXNoLWxpdGU6Z2VuZXJhdGVDb250ZW50"
    url = f"{base64.b64decode(b64_endpoint).decode('utf-8')}?key={api_key}"

    try:
        res = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=25)
        raw_reply = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        clean_json = re.sub(r"```json|```", "", raw_reply).strip()
        parsed = json.loads(clean_json)

        with sqlite3.connect(DB_PATH) as conn:
            for item in parsed.get("pengeluaran", []):
                conn.execute("INSERT INTO pengeluaran (tanggal, kategori, keterangan, nominal, bukti_hash) VALUES (?, ?, ?, ?, ?)",
                             (hari_ini, item.get("kategori", "Umum"), item.get("keterangan", teks_aman), float(item.get("nominal", 0)), bukti_hash))
            for rem in parsed.get("pengingat", []):
                conn.execute("INSERT INTO pengingat (judul, jatuh_tempo) VALUES (?, ?)",
                             (rem.get("judul", teks_aman), rem.get("jatuh_tempo", hari_ini)))
            for note in parsed.get("catatan", []):
                if note.strip():
                    conn.execute("INSERT INTO catatan (tanggal, isi) VALUES (?, ?)", (hari_ini, note.strip()))

        return jsonify({"status": "SUKSES", "hasil": parsed})
    except Exception as e:
        return jsonify({"status": "ERROR", "pesan": f"Gagal memproses AI: {str(e)}"})

@app.route("/selesai-pengingat/<int:id_rem>", methods=["POST"])
def selesai_pengingat(id_rem):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE pengingat SET status='SELESAI' WHERE id=?", (id_rem,))
    return jsonify({"status": "OK"})

@app.route("/hapus-catatan/<int:id_note>", methods=["POST"])
def hapus_catatan(id_note):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM catatan WHERE id=?", (id_note,))
    return jsonify({"status": "OK"})

@app.route("/export-csv", methods=["GET"])
def export_csv():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT id, tanggal, kategori, keterangan, nominal FROM pengeluaran ORDER BY id ASC").fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Tanggal", "Kategori", "Keterangan", "Nominal_Rp"])
    writer.writerows(rows)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=rekap_asisten_mandiri.csv"})


@app.route("/tanya-memori", methods=["POST"])
def tanya_memori():
    data = request.get_json(silent=True) or {}
    pertanyaan = data.get("pertanyaan", "").strip()
    if not pertanyaan:
        return jsonify({"jawaban": "Ketik pertanyaan terlebih dahulu."})

    with sqlite3.connect(DB_PATH) as conn:
        exp = conn.execute("SELECT tanggal, kategori, keterangan, nominal FROM pengeluaran ORDER BY id DESC LIMIT 30").fetchall()
        rem = conn.execute("SELECT judul, jatuh_tempo, status FROM pengingat ORDER BY id DESC LIMIT 20").fetchall()
        notes = conn.execute("SELECT tanggal, isi FROM catatan ORDER BY id DESC LIMIT 30").fetchall()

    konteks_db = f"Data Pengeluaran: {exp}\nData Jadwal: {rem}\nData Catatan: {notes}"
    prompt = f"Kamu adalah SakuAI (Otak Kedua pengguna). Jawab pertanyaan user secara singkat, akurat, dan ramah HANYA berdasarkan data riwayat berikut:\n{konteks_db}\n\nPertanyaan: {pertanyaan}"
    
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    b64_endpoint = "aHR0cHM6Ly9nZW5lcmF0aXZlbGFuZ3VhZ2UuZ29vZ2xlYXBpcy5jb20vdjFiZXRhL21vZGVscy9nZW1pbmktMy41LWZsYXNoLWxpdGU6Z2VuZXJhdGVDb250ZW50"
    url = f"{base64.b64decode(b64_endpoint).decode('utf-8')}?key={api_key}"

    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
        jawaban = res.json()["candidates"]["content"]["parts"]["text"]
        return jsonify({"jawaban": jawaban})
    except Exception as e:
        return jsonify({"jawaban": f"Gagal mencari memori: {e}"})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
