#!/data/data/com.termux/files/usr/bin/sh
# Salin ke ~/.termux/boot/saku.sh  (butuh aplikasi Termux:Boot) agar SakuAI nyala otomatis saat HP hidup.
termux-wake-lock
cd "$HOME/saku-ai" && sh start.sh >> "$HOME/saku-ai/database/jalan.log" 2>&1 &
