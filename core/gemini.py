"""Klien Gemini tunggal yang dipakai API web maupun copilot terminal."""
import time
import requests
from core import config

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiError(Exception):
    """Error yang pesannya aman ditampilkan ke pengguna."""


def generate(parts, json_mode=False, timeout=40) -> str:
    key = config.api_key()
    if len(key) < 10:
        raise GeminiError("GEMINI_API_KEY belum diisi. Buat file .env berisi: GEMINI_API_KEY=kunci_anda")

    body = {"contents": [{"parts": parts}]}
    if json_mode:
        body["generationConfig"] = {"responseMimeType": "application/json"}

    url = ENDPOINT.format(model=config.model_name())
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}

    last = None
    for attempt in range(2):
        try:
            res = requests.post(url, json=body, headers=headers, timeout=timeout)
        except requests.exceptions.RequestException as e:
            last = GeminiError(f"Tidak bisa terhubung ke Gemini (cek internet): {e.__class__.__name__}")
            time.sleep(1)
            continue

        try:
            data = res.json()
        except ValueError:
            data = {}

        if res.status_code in (429, 500, 502, 503) and attempt == 0:
            time.sleep(1.5)
            continue
        if res.status_code != 200:
            msg = (data.get("error") or {}).get("message") or f"HTTP {res.status_code}"
            raise GeminiError(f"Gemini menolak permintaan: {msg}")

        cands = data.get("candidates") or []
        if not cands:
            reason = (data.get("promptFeedback") or {}).get("blockReason")
            raise GeminiError(f"Gemini tidak memberi jawaban{' (diblokir: ' + reason + ')' if reason else ''}.")
        content_parts = (cands[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in content_parts if not p.get("thought"))
        if not text.strip():
            raise GeminiError("Jawaban Gemini kosong. Coba ulangi.")
        return text
    raise last or GeminiError("Gagal menghubungi Gemini.")
