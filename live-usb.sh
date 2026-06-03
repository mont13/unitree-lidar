#!/usr/bin/env bash
# Zivy 3D nahled pres USB/serial. LiDAR musi byt v SERIAL rezimu.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$DIR/unilidar_sdk2/unitree_lidar_sdk/bin/stream_cloud"
VENV="$DIR/.venv/bin/python3"
PORT="${LIDAR_PORT:-/dev/ttyACM0}"
ulimit -c 0
[ -x "$BIN" ] || { echo "CHYBA: chybi $BIN (zkompiluj)"; exit 1; }
[ -e "$PORT" ] || { echo "CHYBA: $PORT neni (USB zapojene?)"; exit 1; }
echo "[live-usb] otevira se 3D okno (Q v okne ukonci)..."
"$BIN" serial | "$VENV" "$DIR/live_view.py"
