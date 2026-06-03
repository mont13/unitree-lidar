#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# START - cteni z Unitree 4D LiDAR L2 pres ETHERNET (point cloud + IMU, zive).
#   - nastavi docasnou IP 192.168.1.2/24 na $IFACE (default eno1, lze prepsat LIDAR_IFACE)
#   - spusti ctecku (zivy vypis); konec: Ctrl+C  nebo z jineho terminalu stop.sh
#
# Predpoklad: LiDAR je v ENET rezimu (tovarni default) a zapojeny RJ45 do $IFACE.
# Pro USB/serial viz README-LIDAR.md.
# ---------------------------------------------------------------------------
set -euo pipefail

# koren odvozeny ze samotneho skriptu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IFACE="${LIDAR_IFACE:-eno1}"
PC_IP="192.168.1.2/24"
LIDAR_IP="192.168.1.62"
BIN="$DIR/unilidar_sdk2/unitree_lidar_sdk/bin/read_udp"

ulimit -c 0  # zadne coredumpy

if [ ! -x "$BIN" ]; then
  echo "[start] CHYBA: chybi binarka $BIN (zkompiluj SDK)." >&2
  exit 1
fi

# bezpecnostni pojistka: nikdy nesahat na hlavni NIC stroje
if ! ip link show "$IFACE" >/dev/null 2>&1; then
  echo "CHYBA: rozhrani $IFACE neexistuje (nastav LIDAR_IFACE=<nic>)." >&2; exit 1
fi
if ip route show default 2>/dev/null | grep -qw "dev $IFACE"; then
  echo "STOP: $IFACE nese default route stroje - odmitam na nej sahat (LIDAR_IFACE=...)." >&2; exit 1
fi

# 1) IP na $IFACE (pridej, pokud chybi)
if ip -br addr show "$IFACE" 2>/dev/null | grep -q "192.168.1.2"; then
  echo "[start] IP 192.168.1.2 uz je na $IFACE"
else
  echo "[start] nastavuji $PC_IP na $IFACE (sudo)"
  sudo ip addr add "$PC_IP" dev "$IFACE"
fi
sudo ip link set "$IFACE" up

# 2) rychla kontrola dosazitelnosti LiDARu
if ping -c1 -W1 "$LIDAR_IP" >/dev/null 2>&1; then
  echo "[start] LiDAR $LIDAR_IP odpovida na ping"
else
  echo "[start] POZOR: LiDAR $LIDAR_IP neodpovida na ping (zkousim cist dal)"
fi

# 3) zivy vypis (Ctrl+C = konec)
echo "[start] spoustim cteni -- Ctrl+C ukonci"
exec "$BIN"
