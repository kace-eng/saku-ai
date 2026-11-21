import hashlib
import json
import re
import sqlite3
import time
from typing import Dict, Any, List

class SovereignEngine:
    def __init__(self, db_path: str = "database/ledger.db", secret_salt: str = "KUNCI_ARSITEK_2026"):
        self.db_path = db_path
        self.secret_salt = secret_salt
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_ledger (
                    block_index INTEGER PRIMARY KEY,
                    timestamp REAL,
                    actor TEXT,
                    clean_context TEXT,
                    numbers_json TEXT,
                    status TEXT,
                    previous_hash TEXT,
                    current_hash TEXT
                )
            """)
            cursor = conn.execute("SELECT COUNT(*) FROM audit_ledger")
            if cursor.fetchone()[0] == 0:
                genesis_hash = self._generate_hash("GENESIS_BLOCK", "0" * 64)
                conn.execute(
                    "INSERT INTO audit_ledger VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (0, time.time(), "SYSTEM", "INITIALIZED", "[]", "GENESIS", "0" * 64, genesis_hash)
                )

    def _generate_hash(self, payload: str, previous_hash: str) -> str:
        raw = f"{previous_hash}|{payload}|{self.secret_salt}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # STEP 1.3: Sensor Privasi Otomatis
    def sanitize_privacy(self, text: str) -> str:
        text = re.sub(r'(\+62|62|0)8[1-9][0-9]{6,10}', '[SENSOR_HP]', text)
        text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[SENSOR_EMAIL]', text)
        text = re.sub(r'\b\d{10,16}\b', '[SENSOR_ID_RAHASIA]', text)
        return text

    # STEP 1.1: Audit Integritas Angka
    def audit_numbers(self, numbers: List[float]) -> Dict[str, Any]:
        if len(numbers) < 4:
            return {"valid": True, "reason": "Data cukup wajar."}
        round_count = sum(1 for n in numbers if n % 1000 == 0 and n > 0)
        if (round_count / len(numbers)) > 0.8:
            return {"valid": False, "reason": "DITOLAK: Lebih dari 80% angka terlalu bulat (indikasi karangan)."}
        return {"valid": True, "reason": "Distribusi angka alami."}

    # STEP 1.2: Simpan Permanen ke Rantai Kriptografi SQLite
    def record_decision(self, actor: str, context: str, numbers: List[float] = None) -> Dict[str, Any]:
        numbers = numbers or []
        clean_text = self.sanitize_privacy(context)
        num_check = self.audit_numbers(numbers)

        if not num_check["valid"]:
            return {"status": "DITOLAK", "alasan": num_check["reason"], "teks_tersensor": clean_text}

        with sqlite3.connect(self.db_path) as conn:
            last_row = conn.execute(
                "SELECT block_index, current_hash FROM audit_ledger ORDER BY block_index DESC LIMIT 1"
            ).fetchone()
            new_index = last_row[0] + 1
            prev_hash = last_row[1]
            ts = time.time()
            nums_str = json.dumps(numbers)

            payload = f"{new_index}|{ts}|{actor}|{clean_text}|{nums_str}"
            curr_hash = self._generate_hash(payload, prev_hash)

            conn.execute(
                "INSERT INTO audit_ledger VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (new_index, ts, actor, clean_text, nums_str, "SAH", prev_hash, curr_hash)
            )

        return {
            "status": "TERKUNCI_DI_DATABASE",
            "block_index": new_index,
            "teks_tersensor": clean_text,
            "hash": curr_hash
        }

    # Verifikasi Integritas Seluruh Database
    def verify_database(self) -> str:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM audit_ledger ORDER BY block_index ASC").fetchall()
            for i in range(1, len(rows)):
                idx, ts, actor, ctx, nums, status, prev_h, curr_h = rows[i]
                expected_prev = rows[i - 1][7]
                if prev_h != expected_prev:
                    return f"BAHAYA! Rantai terputus di Blok #{idx}"
                recalc = self._generate_hash(f"{idx}|{ts}|{actor}|{ctx}|{nums}", prev_h)
                if curr_h != recalc:
                    return f"BAHAYA! Data dimanipulasi di Blok #{idx}"
        return f"AMAN 100%: Semua {len(rows)} blok database utuh dan terverifikasi."

if __name__ == "__main__":
    engine = SovereignEngine()
    print("--- UJI 1: DATA KARANGAN ---")
    print(json.dumps(engine.record_decision("Budi", "Laporan kas", [100000, 200000, 500000, 300000]), indent=2))
    
    print("\n--- UJI 2: DATA VALID + SENSOR PRIVASI ---")
    print(json.dumps(engine.record_decision("Andi", "Transfer ke 123456789012 kontak 081234567890", [42500, 18750, 93000, 15200]), indent=2))
    
    print("\n--- CEK KEAMANAN DATABASE ---")
    print(engine.verify_database())
