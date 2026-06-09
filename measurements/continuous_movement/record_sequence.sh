#!/usr/bin/env bash
# Nahraje kratkou USB/serial sekvenci framu pro lidar-only SLAM.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
PY="${PYTHON:-python3}"
if [ -x "$ROOT/.venv/bin/python3" ]; then
  PY="$ROOT/.venv/bin/python3"
fi
STAMP="$(date +%Y%m%d_%H%M%S)"
FRAMES="${FRAMES:-150}"
DURATION_SECONDS="${DURATION_SECONDS:-${RECORD_SECONDS:-30}}"
PACKETS_PER_FRAME="${PACKETS_PER_FRAME:-20}"
OUT_DIR="${OUT_DIR:-$DIR/scans/seq_$STAMP}"
exec "$PY" "$ROOT/record_serial_sequence_direct.py" \
  --frames "$FRAMES" \
  --seconds "$DURATION_SECONDS" \
  --packets-per-frame "$PACKETS_PER_FRAME" \
  --out-dir "$OUT_DIR" \
  "$@"
