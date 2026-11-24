"""Konfigurasi bersama: path, .env, dan pengaturan Gemini."""
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "database")
WEB_DIR = os.path.join(BASE_DIR, "web")
os.makedirs(DATA_DIR, exist_ok=True)

APP_DB = os.path.join(DATA_DIR, "asisten_pribadi.db")
LEDGER_DB = os.path.join(DATA_DIR, "ledger.db")


def load_env(path=None):
    """Baca file .env sederhana. Variabel yang sudah diset di sistem tidak ditimpa."""
    path = path or os.path.join(BASE_DIR, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)


load_env()


def api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def model_name() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()


def ledger_salt() -> str:
    return os.environ.get("LEDGER_SALT", "KUNCI_ARSITEK_2026")
