#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Prepne LiDAR ze SERIAL do ETHERNET rezimu (workMode 0).
# Prikaz se posila PRES SERIAL (/dev/ttyACM* nebo LIDAR_PORT) - LiDAR ted posloucha na serialu.
# Po odeslani je NUTNE LiDAR vypnout a zapnout (power-cycle)!
# ---------------------------------------------------------------------------
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$DIR/unilidar_sdk2/unitree_lidar_sdk/bin/set_to_udp_mode"
ulimit -c 0

if [ -z "${LIDAR_PORT:-}" ]; then
  PORT=""
  for dev in /dev/ttyACM* /dev/ttyUSB*; do
    if [ -e "$dev" ]; then PORT="$dev"; break; fi
  done
  PORT="${PORT:-/dev/ttyACM0}"
else
  PORT="$LIDAR_PORT"
fi
export LIDAR_PORT="$PORT"

[ -x "$BIN" ] || { echo "CHYBA: chybi $BIN (zkompiluj SDK)" >&2; exit 1; }
[ -e "$PORT" ] || { echo "CHYBA: $PORT neexistuje (je USB zapojene? nastav LIDAR_PORT=<port>)" >&2; exit 1; }

CMD=("$BIN")
if [ "$(id -u)" -ne 0 ] && { [ ! -r "$PORT" ] || [ ! -w "$PORT" ]; }; then
  echo "[switch-to-ethernet] Nemam prava k $PORT ($(stat -c '%A %U:%G' "$PORT" 2>/dev/null || echo 'neznamy vlastnik'))." >&2
  echo "[switch-to-ethernet] Trvale: sudo usermod -aG dialout $USER  # potom odhlasit/prihlasit" >&2
  echo "[switch-to-ethernet] Zkousim jednorazove sudo..." >&2
  CMD=(sudo env "LIDAR_PORT=$PORT" "$BIN")
fi

echo "Posilam prepnuti na ETHERNET (workMode 0) pres serial $PORT ..."
timeout 10 "${CMD[@]}" || true

cat <<'EOF'

>>> HOTOVO: prikaz 'ethernet mode' odeslan.
>>> TED VYPNI A ZAPNI NAPAJENI LiDARu (power-cycle) - jinak se zmena neprojevi.
>>> Po restartu spust:   ./start.sh
EOF
