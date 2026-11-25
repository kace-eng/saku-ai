#!/usr/bin/env sh
# Jalankan SakuAI lengkap (server + pengingat + penangkap transaksi).
# Setiap proses dijaga: bila berhenti karena error, otomatis dinyalakan lagi dalam 5 detik.
cd "$(dirname "$0")" || exit 1
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock   # cegah Android menidurkan proses
trap 'kill 0' INT TERM EXIT

jaga() {  # keluar bersih (kode 0) = sengaja berhenti, selain itu nyalakan ulang
  while true; do
    "$@"
    [ $? -eq 0 ] && break
    echo "[start] $1 $2 berhenti, mulai ulang 5 detik lagi..."
    sleep 5
  done
}

jaga python api/main.py &
jaga python notifier.py &
jaga python penangkap.py &
wait
