#!/usr/bin/env bash
# Rychla kontrola komponent pro continuous_movement experiment.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
PY="${PYTHON:-python3}"
[ -x "$ROOT/.venv/bin/python3" ] && PY="$ROOT/.venv/bin/python3"

echo "ROOT: $ROOT"
echo "Python: $PY"
if [ -x "$ROOT/.venv/bin/python3" ]; then
  echo "venv: OK ($ROOT/.venv/bin/python3)"
else
  echo "venv: CHYBI (live preview a KISS-ICP budou chtit .venv)"
fi
for bin in stream_cloud record_seq; do
  if [ -x "$ROOT/unilidar_sdk2/unitree_lidar_sdk/bin/$bin" ]; then
    echo "SDK bin $bin: OK"
  else
    echo "SDK bin $bin: CHYBI"
  fi
done
if [ -e "${LIDAR_PORT:-/dev/ttyACM0}" ]; then
  echo "serial port ${LIDAR_PORT:-/dev/ttyACM0}: existuje"
else
  echo "serial port ${LIDAR_PORT:-/dev/ttyACM0}: neexistuje / LiDAR neni pripojeny"
fi
if [ -n "${DISPLAY:-}" ]; then
  echo "DISPLAY: $DISPLAY"
else
  echo "DISPLAY: neni nastaveny (Open3D okno se bez GUI neotevre)"
fi
"$PY" - <<'PY'
import importlib.util
mods = ["numpy", "matplotlib", "open3d", "kiss_icp", "rerun"]
for mod in mods:
    print(f"python modul {mod}:", "OK" if importlib.util.find_spec(mod) else "CHYBI")
PY
