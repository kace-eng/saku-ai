#!/usr/bin/env sh
# Jalankan server SakuAI + pengingat otomatis sekaligus.
cd "$(dirname "$0")" || exit 1
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock   # cegah Android menidurkan proses
trap 'kill 0' INT TERM EXIT
python api/main.py &
python notifier.py &
wait
