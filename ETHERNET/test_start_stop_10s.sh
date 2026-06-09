#!/usr/bin/env bash
set +e

LIDAR_IP="${LIDAR_IP:-192.168.1.62}"
LOCAL_IP="${LOCAL_IP:-192.168.1.2}"
WAIT_SECONDS="${WAIT_SECONDS:-10}"
REPEAT="${REPEAT:-5}"

cd "$(dirname "$0")"

echo "=== Unitree LiDAR Ethernet start -> wait ${WAIT_SECONDS}s -> standby ==="
echo "LiDAR: ${LIDAR_IP}:6101"
echo "PC:    ${LOCAL_IP}:6201"
echo

echo "=== START LiDAR rotation ==="
python3 ./unitree_lidar_udp_cmd.py \
  --local-ip "${LOCAL_IP}" \
  --lidar-ip "${LIDAR_IP}" \
  --start \
  --repeat "${REPEAT}" \
  --listen 1
start_rc=$?
echo "Start command exit code: ${start_rc}"
echo

echo "=== Waiting ${WAIT_SECONDS} seconds for spin-up ==="
sleep "${WAIT_SECONDS}"
echo

echo "=== STOP/STANDBY LiDAR rotation ==="
python3 ./unitree_lidar_udp_cmd.py \
  --local-ip "${LOCAL_IP}" \
  --lidar-ip "${LIDAR_IP}" \
  --standby \
  --repeat "${REPEAT}" \
  --listen 2
stop_rc=$?
echo "Stop command exit code: ${stop_rc}"
echo

echo "NOTE: This LiDAR may not return a parsed ACK. If the motor physically starts/stops, the command worked."

# Keep wrapper successful so shell pipelines don't look failed only because ACK was not parsed.
exit 0
