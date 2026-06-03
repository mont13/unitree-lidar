#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Prepne LiDAR z ETHERNET do SERIAL rezimu (workMode 8).
# Prikaz se posila PRES ETHERNET (LiDAR ted posloucha na ethernetu).
# Po odeslani je NUTNE LiDAR vypnout a zapnout (power-cycle)!
# ---------------------------------------------------------------------------
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IFACE="${LIDAR_IFACE:-eno1}"; PC_IP="192.168.1.2/24"; LIDAR_IP="192.168.1.62"
BIN="$DIR/unilidar_sdk2/unitree_lidar_sdk/bin/set_to_serial_mode"
ulimit -c 0
[ -x "$BIN" ] || { echo "CHYBA: chybi $BIN (zkompiluj SDK)"; exit 1; }

# bezpecnostni pojistka: nikdy nesahat na hlavni NIC stroje
if ! ip link show "$IFACE" >/dev/null 2>&1; then
  echo "CHYBA: rozhrani \$IFACE neexistuje (nastav LIDAR_IFACE=<nic>)." >&2; exit 1
fi
if ip route show default 2>/dev/null | grep -qw "dev $IFACE"; then
  echo "STOP: \$IFACE nese default route stroje - odmitam na nej sahat (LIDAR_IFACE=...)." >&2; exit 1
fi

ip -br addr show "$IFACE" | grep -q 192.168.1.2 || sudo ip addr add "$PC_IP" dev "$IFACE"
sudo ip link set "$IFACE" up
if ping -c1 -W1 "$LIDAR_IP" >/dev/null 2>&1; then
  echo "LiDAR $LIDAR_IP odpovida, posilam prepnuti na SERIAL (workMode 8)..."
else
  echo "POZOR: LiDAR neodpovida na ping, presto zkousim odeslat prikaz..."
fi
timeout 10 "$BIN" || true

cat <<'EOF'

>>> HOTOVO: prikaz 'serial mode' odeslan.
>>> TED VYPNI A ZAPNI NAPAJENI LiDARu (power-cycle) - jinak se zmena neprojevi.
>>> Po restartu spust:   ./start-usb.sh
>>> (Ethernet ted prestane posilat data. Zpet na ethernet: ./switch-to-ethernet.sh)
EOF
