#!/usr/bin/env bash
set +e
LIDAR_IP="${LIDAR_IP:-192.168.1.62}"
LOCAL_IP="${LOCAL_IP:-192.168.1.2}"
cd "$(dirname "$0")"
echo "Setting Unitree LiDAR work-mode 8 = serial mode. Power-cycle LiDAR afterwards."
python3 ./unitree_lidar_udp_cmd.py --local-ip "${LOCAL_IP}" --lidar-ip "${LIDAR_IP}" --work-mode 8 --repeat 3 --listen 2
echo "NOW POWER-CYCLE THE LIDAR if you really wanted serial mode."
