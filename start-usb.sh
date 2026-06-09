#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# START USB - cteni z Unitree L2 pres USB/SERIAL (/dev/ttyACM* nebo LIDAR_PORT).
# Funguje az kdyz je LiDAR v SERIAL rezimu (viz switch-to-serial.sh + power-cycle).
# Konec: Ctrl+C  nebo z jineho terminalu ./stop.sh
# ---------------------------------------------------------------------------
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$DIR/unilidar_sdk2/unitree_lidar_sdk/bin/read_serial"
ulimit -c 0

if [ -z "${LIDAR_PORT:-}" ]; then
  PORT=""
  for dev in /dev/ttyACM* /dev/ttyUSB*; do
    if [ -e "$dev" ]; then PORT="$dev"; break; fi
  done
  PORT="${PORT:-/dev/ttyACM0}"
else
  PORT="$LIDAR_PORT"
fi
export LIDAR_PORT="$PORT"

[ -x "$BIN" ] || { echo "CHYBA: chybi $BIN (zkompiluj SDK)" >&2; exit 1; }
[ -e "$PORT" ] || { echo "CHYBA: $PORT neexistuje (je USB zapojene? nastav LIDAR_PORT=<port>)" >&2; exit 1; }

CMD=("$BIN")
if [ "$(id -u)" -ne 0 ] && { [ ! -r "$PORT" ] || [ ! -w "$PORT" ]; }; then
  echo "[start-usb] Nemam prava k $PORT ($(stat -c '%A %U:%G' "$PORT" 2>/dev/null || echo 'neznamy vlastnik'))." >&2
  echo "[start-usb] Trvale: sudo usermod -aG dialout $USER  # potom odhlasit/prihlasit" >&2
  echo "[start-usb] Zkousim jednorazove sudo..." >&2
  CMD=(sudo env "LIDAR_PORT=$PORT" "$BIN")
fi

echo "[start-usb] ctu z $PORT -- Ctrl+C ukonci"
exec "${CMD[@]}"
