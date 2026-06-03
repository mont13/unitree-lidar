#!/usr/bin/env bash
# Zivy 3D nahled pres ETHERNET. LiDAR musi byt v ENET rezimu.
set -euo pipefail
# koren odvozeny ze samotneho skriptu (zadne hardcoded cesty)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$DIR/unilidar_sdk2/unitree_lidar_sdk/bin/stream_cloud"
VENV="$DIR/.venv/bin/python3"
IFACE="${LIDAR_IFACE:-eno1}"; PC_IP=192.168.1.2/24
ulimit -c 0
[ -x "$BIN" ] || { echo "CHYBA: chybi $BIN (zkompiluj)"; exit 1; }

# bezpecnostni pojistka: nikdy nesahat na hlavni NIC stroje
if ! ip link show "$IFACE" >/dev/null 2>&1; then
  echo "CHYBA: rozhrani \$IFACE neexistuje (nastav LIDAR_IFACE=<nic>)." >&2; exit 1
fi
if ip route show default 2>/dev/null | grep -qw "dev $IFACE"; then
  echo "STOP: \$IFACE nese default route stroje - odmitam na nej sahat (LIDAR_IFACE=...)." >&2; exit 1
fi

ip -br addr show "$IFACE" | grep -q 192.168.1.2 || sudo ip addr add "$PC_IP" dev "$IFACE"
sudo ip link set "$IFACE" up
echo "[live-ethernet] otevira se 3D okno (Q v okne ukonci)..."
"$BIN" udp | "$VENV" "$DIR/live_view.py"
