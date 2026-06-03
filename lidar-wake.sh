#!/usr/bin/env bash
# Probudi LiDAR - spusti rotaci (zacne zase merit/posilat data).

# koren odvozen ze samotneho skriptu (zadne hardcoded cesty)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# SDK binarka pro ovladani motoru LiDARu
BIN="$DIR/unilidar_sdk2/unitree_lidar_sdk/bin/lidar_motor"

exec "$BIN" start serial
