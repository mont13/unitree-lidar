#!/usr/bin/env bash
# Ztisi LiDAR - zastavi rotaci (standby, ~1W, bez hukotu). Probudit: ./lidar-wake.sh
set -euo pipefail

# Koren odvozen ze samotneho skriptu (zadne hardcoded cesty)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# SDK binarka pro ovladani motoru LiDARu
BIN="$DIR/unilidar_sdk2/unitree_lidar_sdk/bin/lidar_motor"

# Serovy port LiDARu (lze prepsat pres LIDAR_PORT)
PORT="${LIDAR_PORT:-/dev/ttyACM0}"

# Kontrola, ze binarka existuje a je spustitelna
if [ ! -x "$BIN" ]; then
  echo "CHYBA: binarka '$BIN' neexistuje nebo neni spustitelna." >&2
  exit 1
fi

# Kontrola, ze serovy port (zarizeni) existuje
if [ ! -e "$PORT" ]; then
  echo "CHYBA: serovy port '$PORT' neexistuje (nastav LIDAR_PORT=<port>)." >&2
  exit 1
fi

exec "$BIN" stop serial
