#!/usr/bin/env bash
# Otevre mracno v Rerun prohlizeci (plynula navigace: orbit + first-person prolet).
# Pouziti: ./rerun-view.sh [mracno.pcd]   (default room_map_full.pcd)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/.venv/bin/python3" "$DIR/rerun_view.py" "$@"
