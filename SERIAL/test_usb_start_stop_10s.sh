#!/usr/bin/env bash
set +e
PORT="${PORT:-/dev/ttyACM0}"
WAIT_SECONDS="${WAIT_SECONDS:-10}"
REPEAT="${REPEAT:-5}"
cd "$(dirname "$0")"

echo "=== Unitree LiDAR USB start -> wait ${WAIT_SECONDS}s -> standby ==="
echo "PORT: ${PORT}"
echo

echo "=== START LiDAR rotation over USB ==="
sudo python3 ./unitree_lidar_usb_standby.py --port "${PORT}" --start --repeat "${REPEAT}" --listen 2
start_rc=$?
echo "Start command exit code: ${start_rc}"
echo

echo "=== Waiting ${WAIT_SECONDS} seconds for spin-up ==="
sleep "${WAIT_SECONDS}"
echo

echo "=== STOP/STANDBY LiDAR rotation over USB ==="
sudo python3 ./unitree_lidar_usb_standby.py --port "${PORT}" --standby --repeat "${REPEAT}" --listen 2
stop_rc=$?
echo "Stop command exit code: ${stop_rc}"
echo

echo "If motor physically started and then stopped, USB/SERIAL control works."
exit 0
