#!/usr/bin/env sh
# Pasang SakuAI agar jalan sendiri saat HP menyala + pintasan catat-suara di layar utama.
# Jalankan SEKALI dari folder proyek:  sh termux/pasang.sh
DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
mkdir -p "$HOME_DIR/.termux/boot" "$HOME_DIR/.shortcuts" "$DIR/database"

cat > "$HOME_DIR/.termux/boot/saku.sh" <<BOOT
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
cd "$DIR" && sh start.sh >> "$DIR/database/jalan.log" 2>&1 &
BOOT

cat > "$HOME_DIR/.shortcuts/SakuAI-catat-suara" <<WIDGET
#!/data/data/com.termux/files/usr/bin/sh
cd "$DIR" && python catat_suara.py
WIDGET

chmod +x "$HOME_DIR/.termux/boot/saku.sh" "$HOME_DIR/.shortcuts/SakuAI-catat-suara"

echo "✔ Nyala-otomatis dipasang : $HOME_DIR/.termux/boot/saku.sh"
echo "✔ Pintasan suara dipasang : $HOME_DIR/.shortcuts/SakuAI-catat-suara"
echo
for c in termux-notification termux-speech-to-text curl; do
  command -v "$c" >/dev/null 2>&1 && echo "  ok      $c" || echo "  KURANG  $c  (pkg install termux-api curl)"
done
echo
echo "Langkah manual yang tersisa (sekali saja):"
echo " 1. Pasang aplikasi Termux:Boot dan Termux:Widget (satu sumber dengan Termux), buka Termux:Boot satu kali."
echo " 2. Layar utama → tambah widget 'Termux:Widget' → pilih 'SakuAI-catat-suara'."
echo " 3. Setelan Android → Baterai → Termux → Tanpa pembatasan."
