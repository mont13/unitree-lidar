#!/usr/bin/env bash
# Otevre interaktivni 3D prohlizec zachyceneho mracna (lidar_cloud.pcd).
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/.venv/bin/python3" "$DIR/view_pcd.py" "$@"
