#!/usr/bin/env bash
# Slozi posledni sekvenci kratkych PCD framu do jedne mapy pomoci KISS-ICP.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
PY="${PYTHON:-$ROOT/.venv/bin/python3}"
SEQ="${1:-$DIR/scans/latest_sequence}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${2:-$DIR/results/continuous_map_$STAMP.pcd}"
VOXEL="${3:-0.03}"

if [ ! -x "$PY" ]; then
  echo "CHYBA: chybi Python venv: $PY" >&2
  echo "Vytvor ho v kořeni repa:" >&2
  echo "  python3.12 -m venv .venv" >&2
  echo "  .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi
if [ ! -d "$SEQ" ]; then
  echo "CHYBA: sekvence neexistuje: $SEQ" >&2
  echo "Nejdriv spust: measurements/continuous_movement/record_sequence.sh" >&2
  exit 1
fi
mkdir -p "$(dirname "$OUT")"
"$PY" "$ROOT/slam_map.py" "$SEQ" "$OUT" "$VOXEL"
OUT_DIR="$(cd "$(dirname "$OUT")" && pwd)"
OUT_BASE="$(basename "$OUT")"
PNG="${OUT%.*}.png"
ln -sfn "$OUT_BASE" "$OUT_DIR/latest_map.pcd"
if [ -f "$PNG" ]; then
  ln -sfn "$(basename "$PNG")" "$OUT_DIR/latest_map.png"
fi
echo "latest map: $OUT_DIR/latest_map.pcd"
[ -f "$PNG" ] && echo "latest png: $OUT_DIR/latest_map.png"
