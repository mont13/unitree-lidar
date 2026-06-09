#!/usr/bin/env bash
# Fallback slozeni mapy bez .venv/Open3D/KISS-ICP; pouziva systemovy python3 + scipy.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
PY="${PYTHON_SIMPLE:-python3}"
SEQ="${1:-$DIR/scans/latest_sequence}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${2:-$DIR/results/continuous_map_simple_$STAMP.pcd}"
"$PY" "$ROOT/continuous_map_simple.py" "$SEQ" "$OUT"
