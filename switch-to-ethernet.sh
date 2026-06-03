#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Prepne LiDAR ze SERIAL do ETHERNET rezimu (workMode 0).
# Prikaz se posila PRES SERIAL (/dev/ttyACM0) - LiDAR ted posloucha na serialu.
# Po odeslani je NUTNE LiDAR vypnout a zapnout (power-cycle)!
# ---------------------------------------------------------------------------
set -euo pipefail
# koren odvozeny ze samotneho skriptu (zadne hardcoded cesty)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${LIDAR_PORT:-/dev/ttyACM0}"
BIN="$DIR/unilidar_sdk2/unitree_lidar_sdk/bin/set_to_udp_mode"
ulimit -c 0
[ -x "$BIN" ] || { echo "CHYBA: chybi $BIN (zkompiluj SDK)"; exit 1; }
[ -e "$PORT" ] || { echo "CHYBA: $PORT neexistuje (je USB zapojene?)"; exit 1; }

echo "Posilam prepnuti na ETHERNET (workMode 0) pres serial $PORT ..."
timeout 10 "$BIN" || true

cat <<'EOF'

>>> HOTOVO: prikaz 'ethernet mode' odeslan.
>>> TED VYPNI A ZAPNI NAPAJENI LiDARu (power-cycle) - jinak se zmena neprojevi.
>>> Po restartu spust:   ./start.sh
EOF
