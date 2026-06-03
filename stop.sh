#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# STOP - ukonci cteni LiDARu a vrati sit do PUVODNIHO stavu.
#   - zabije bezici ctecky (read_udp / read_serial)
#   - odebere docasnou IP 192.168.1.2/24 z $IFACE ($IFACE byl puvodne bez IP)
# ---------------------------------------------------------------------------
set -uo pipefail

# koren odvozen ze samotneho skriptu (ne hardcoded cesta)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IFACE="${LIDAR_IFACE:-eno1}"
PC_IP="192.168.1.2/24"

echo "[stop] ukoncuji ctecky LiDARu ..."
pkill -f "bin/read_udp"    2>/dev/null && echo "  read_udp ukoncen"    || echo "  read_udp nebezel"
pkill -f "bin/read_serial" 2>/dev/null && echo "  read_serial ukoncen" || true

if ip -br addr show "$IFACE" 2>/dev/null | grep -q "192.168.1.2"; then
  echo "[stop] odebiram IP $PC_IP z $IFACE (navrat do puvodniho stavu)"

  # bezpecnostni pojistka: nikdy nesahat na hlavni NIC stroje
  if ! ip link show "$IFACE" >/dev/null 2>&1; then
    echo "CHYBA: rozhrani $IFACE neexistuje (nastav LIDAR_IFACE=<nic>)." >&2; exit 1
  fi
  if ip route show default 2>/dev/null | grep -qw "dev $IFACE"; then
    echo "STOP: $IFACE nese default route stroje - odmitam na nej sahat (LIDAR_IFACE=...)." >&2; exit 1
  fi

  sudo ip addr del "$PC_IP" dev "$IFACE"
else
  echo "[stop] IP na $IFACE neni nastavena, nic neodebiram"
fi

echo "[stop] hotovo - $IFACE je zpatky v puvodnim stavu (bez IP, link zustava UP)."
