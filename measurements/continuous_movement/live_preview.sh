#!/usr/bin/env bash
# Spusti existujici real-time Open3D nahled jako soucast continuous_movement.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
MODE="${1:-usb}"
case "$MODE" in
  usb|serial)
    exec "$ROOT/live-usb.sh"
    ;;
  ethernet|enet|udp)
    exec "$ROOT/live-ethernet.sh"
    ;;
  *)
    echo "Pouziti: $0 [usb|ethernet]" >&2
    exit 2
    ;;
esac
