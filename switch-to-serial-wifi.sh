#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Prepne LiDAR z ETHERNET do SERIAL rezimu (workMode 8) pres WI-FI.
# LiDAR musi byt pripojen ethernetovym kabelem do LAN portu Wi-Fi routeru.
# ---------------------------------------------------------------------------
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IFACE="${LIDAR_WIFI_IFACE:-${LIDAR_IFACE:-wlp1s0}}"
PC_IP="192.168.1.2/24"
LIDAR_IP="192.168.1.62"
BIN="$DIR/unilidar_sdk2/unitree_lidar_sdk/bin/set_to_serial_mode"

[ -x "$BIN" ] || { echo "CHYBA: chybi $BIN (zkompiluj SDK)"; exit 1; }

echo "Pridavam docasnou IP $PC_IP na rozhrani $IFACE (sudo)..."
ip -br addr show "$IFACE" 2>/dev/null | grep -q "192.168.1.2" || sudo ip addr add "$PC_IP" dev "$IFACE"

echo "Zkousim pingnout LiDAR na $LIDAR_IP pres Wi-Fi..."
if ping -c 2 -W 2 "$LIDAR_IP" >/dev/null 2>&1; then
  echo "LiDAR $LIDAR_IP odpovida! Posilam prepnuti do SERIAL rezimu..."
  timeout 5 "$BIN" || true
  echo ""
  echo ">>> HOTOVO: Prikaz odeslan!"
  echo ">>> TED VYPNI A ZAPNI NAPAJENI LiDARu (power-cycle 12V DC)!"
  echo ">>> Po restartu uz bude LiDAR v sériovém režimu a muzes ho pouzivat pres USB."
else
  echo "CHYBA: LiDAR na $LIDAR_IP neodpovida. Ujisti se, ze:"
  echo "  1. LiDAR je propojen ethernetovym kabelem s LAN portem routeru / site dostupne z rozhrani $IFACE."
  echo "  2. LiDAR je zapojen do 12V napajeni a bezi."
fi

echo "Odebiram docasnou IP z rozhrani $IFACE..."
sudo ip addr del "$PC_IP" dev "$IFACE" 2>/dev/null || true
