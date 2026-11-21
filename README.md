# 🤖 Asisten Pribadi Mandiri (AI Expense & Smart Reminder + Privacy Guardrail)

Aplikasi asisten pribadi berbasis web (*Neo-Brutalism UI*) yang mengubah catatan bahasa sehari-hari menjadi rekap pengeluaran terstruktur dan pengingat jadwal otomatis (servis kendaraan, tagihan, tugas) dengan perlindungan sensor privasi otomatis.

## ✨ Fitur Utama
- **Natural Language AI Parser:** Cukup ketik kalimat santai, AI otomatis memisahkan nominal pengeluaran dan menghitung tanggal jatuh tempo pengingat.
- **Zero-Trust Privacy Guardrail:** Nomor rekening, telepon, dan identitas sensitif otomatis disensor sebelum diproses AI.
- **Dashboard Interaktif & Ekspor CSV:** Papan peringatan jatuh tempo berkode warna, total pengeluaran *real-time*, dan unduh laporan ke Excel (`.csv`).
- **Terminal AI Co-Pilot (`copilot.py`):** Asisten pemrograman langsung di terminal.

## 🚀 Cara Menjalankan (Di HP Termux maupun Laptop)
1. Instal dependensi: `pip install flask requests`
2. Buat file `.env` berisi: `GEMINI_API_KEY=kunci_api_anda`
3. Jalankan server: `python api/main.py`
4. Buka browser ke `http://127.0.0.1:8000`
