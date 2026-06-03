#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# START USB - cteni z Unitree L2 pres USB/SERIAL (/dev/ttyACM0).
# Funguje az kdyz je LiDAR v SERIAL rezimu (viz switch-to-serial.sh + power-cycle).
# Konec: Ctrl+C  nebo z jineho terminalu ./stop.sh
# ---------------------------------------------------------------------------
set -euo pipefail
# koren odvozen ze samotneho skriptu (zadna hardcoded cesta)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${LIDAR_PORT:-/dev/ttyACM0}"
BIN="$DIR/unilidar_sdk2/unitree_lidar_sdk/bin/read_serial"
ulimit -c 0
[ -x "$BIN" ] || { echo "CHYBA: chybi $BIN (zkompiluj SDK)"; exit 1; }
[ -e "$PORT" ] || { echo "CHYBA: $PORT neexistuje (je USB zapojene?)"; exit 1; }

echo "[start-usb] ctu z $PORT -- Ctrl+C ukonci"
exec "$BIN"
