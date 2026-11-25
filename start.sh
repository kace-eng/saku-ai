#!/usr/bin/env sh
# Jalankan SakuAI lengkap (server + pengingat + penangkap transaksi).
# Setiap proses dijaga: bila berhenti karena error, otomatis dinyalakan lagi dalam 5 detik.
cd "$(dirname "$0")" || exit 1
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock   # cegah Android menidurkan proses

SELESAI=0
berhenti() {
  [ "$SELESAI" = 1 ] && return   # cegah pemanggilan ganda (INT/TERM lalu EXIT)
  SELESAI=1
  trap "" INT TERM               # abaikan sinyal susulan agar tidak terjadi pemanggilan berulang
  kill 0 2>/dev/null             # hentikan seluruh proses SakuAI di grup ini
  exit 0
}
trap berhenti INT TERM EXIT

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
