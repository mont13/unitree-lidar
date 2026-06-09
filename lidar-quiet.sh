#!/usr/bin/env bash
# Ztisi LiDAR - zastavi rotaci (standby, ~1W, bez hukotu). Probudit: ./lidar-wake.sh
set -euo pipefail

# Koren odvozen ze samotneho skriptu (zadne hardcoded cesty)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# SDK binarka pro ovladani motoru LiDARu
BIN="$DIR/unilidar_sdk2/unitree_lidar_sdk/bin/lidar_motor"

# Rezim lze vynutit argumentem: serial / udp. Bez argumentu auto.
# Serial pouzije LIDAR_PORT nebo automaticky najde /dev/ttyACM* /dev/ttyUSB*.
# UDP pouzije LIDAR_IFACE (default eno1) a bezpecnostni guard proti default route.
# shellcheck source=/dev/null
source "$DIR/lidar-motor-lib.sh"

lidar_motor_main "$BIN" stop "${1:-}"
