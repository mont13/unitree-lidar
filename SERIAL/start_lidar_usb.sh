#!/usr/bin/env bash
set +e
PORT="${PORT:-/dev/ttyACM0}"
cd "$(dirname "$0")"
sudo python3 ./unitree_lidar_usb_standby.py --port "${PORT}" --start --repeat 5 --listen 2
