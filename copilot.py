import os, sys, base64, requests

if os.path.exists(".env"):
    for line in open(".env"):
        if "=" in line and not line.startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ[k] = v

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

def tanya_ai(perintah, isi_file=""):
    if len(API_KEY) < 10:
        return "ERROR: GEMINI_API_KEY di .env masih kosong."
    prompt = f"Kamu Senior Software Architect di Termux. Jawab singkat dan langsung ke solusi kode.\n\n{isi_file}\n\nPermintaan: {perintah}"
    
    # Alamat resmi server Gemini disandikan Base64 agar tidak terpotong clipboard/chat
    b64_endpoint = "aHR0cHM6Ly9nZW5lcmF0aXZlbGFuZ3VhZ2UuZ29vZ2xlYXBpcy5jb20vdjFiZXRhL21vZGVscy9nZW1pbmktMy41LWZsYXNoLWxpdGU6Z2VuZXJhdGVDb250ZW50"
    endpoint = base64.b64decode(b64_endpoint).decode("utf-8")
    url_lengkap = f"{endpoint}?key={API_KEY}"
    
    try:
        res = requests.post(url_lengkap, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
        data = res.json()
        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        return f"Respon API: {data}"
    except Exception as e:
        return f"Gagal koneksi: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Pakai: python copilot.py 'pertanyaan' [file_opsional]")
        sys.exit(0)
    konteks = ""
    if len(sys.argv) >= 3 and os.path.exists(sys.argv):
        konteks = f"ISI FILE {sys.argv}:\n" + open(sys.argv).read()
    print("\n🤖 AI Co-Pilot:\n")
    print(tanya_ai(sys.argv, konteks))
