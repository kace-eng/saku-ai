"""AI Co-Pilot terminal.  Pakai: python copilot.py 'pertanyaan' [file1 file2 ...]"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from core.gemini import GeminiError, generate  # noqa: E402

MAX_FILE = 60_000  # karakter per file


def tanya_ai(perintah, isi_file=""):
    prompt = ("Kamu Senior Software Architect. Jawab singkat dan langsung ke solusi kode, "
              f"dalam bahasa Indonesia.\n\n{isi_file}\n\nPermintaan: {perintah}")
    try:
        return generate([{"text": prompt}], timeout=60)
    except GeminiError as e:
        return f"ERROR: {e}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Pakai: python copilot.py 'pertanyaan' [file_opsional ...]")
        sys.exit(0)
    konteks = ""
    for path in sys.argv[2:]:
        if os.path.isfile(path):
            with open(path, encoding="utf-8", errors="replace") as f:
                konteks += f"ISI FILE {path}:\n{f.read(MAX_FILE)}\n\n"
        else:
            print(f"(file tidak ditemukan, dilewati: {path})")
    print("\n🤖 AI Co-Pilot:\n")
    print(tanya_ai(sys.argv[1], konteks))
