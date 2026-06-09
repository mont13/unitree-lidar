#!/usr/bin/env bash
set +e
LIDAR_IP="${LIDAR_IP:-192.168.1.62}"
LOCAL_IP="${LOCAL_IP:-192.168.1.2}"
cd "$(dirname "$0")"
python3 ./unitree_lidar_udp_cmd.py --local-ip "${LOCAL_IP}" --lidar-ip "${LIDAR_IP}" --start --repeat 5 --listen 1
