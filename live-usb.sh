#!/usr/bin/env bash
# Zivy 3D nahled pres USB/serial. LiDAR musi byt v SERIAL rezimu.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$DIR/unilidar_sdk2/unitree_lidar_sdk/bin/stream_cloud"
VENV="$DIR/.venv/bin/python3"
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

[ -x "$BIN" ] || { echo "CHYBA: chybi $BIN (zkompiluj)" >&2; exit 1; }
[ -x "$VENV" ] || { echo "CHYBA: chybi $VENV (vytvor .venv)" >&2; exit 1; }
[ -e "$PORT" ] || { echo "CHYBA: $PORT neni (USB zapojene? nastav LIDAR_PORT=<port>)" >&2; exit 1; }

STREAM_CMD=("$BIN" serial)
if [ "$(id -u)" -ne 0 ] && { [ ! -r "$PORT" ] || [ ! -w "$PORT" ]; }; then
  echo "[live-usb] Nemam prava k $PORT ($(stat -c '%A %U:%G' "$PORT" 2>/dev/null || echo 'neznamy vlastnik'))." >&2
  echo "[live-usb] Trvale: sudo usermod -aG dialout $USER  # potom odhlasit/prihlasit" >&2
  echo "[live-usb] Zkousim jednorazove sudo pro SDK ctecku..." >&2
  STREAM_CMD=(sudo env "LIDAR_PORT=$PORT" "$BIN" serial)
fi

echo "[live-usb] otevira se 3D okno (Q v okne ukonci)..."
"${STREAM_CMD[@]}" | "$VENV" "$DIR/live_view.py"
