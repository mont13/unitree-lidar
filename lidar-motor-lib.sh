#!/usr/bin/env bash
# Sdilena logika pro lidar-quiet.sh / lidar-wake.sh.
# Umí serial i ethernet/UDP; v auto rezimu nejdriv zkusi serial a potom UDP.
set -euo pipefail

lidar_find_serial_port() {
  if [ -n "${LIDAR_PORT:-}" ]; then
    printf '%s\n' "$LIDAR_PORT"
    return 0
  fi

  local dev
  for dev in /dev/ttyACM* /dev/ttyUSB*; do
    if [ -e "$dev" ]; then
      printf '%s\n' "$dev"
      return 0
    fi
  done

  printf '%s\n' "/dev/ttyACM0"
}

lidar_run_motor_serial() {
  local bin="$1" cmd="$2" port
  port="$(lidar_find_serial_port)"
  export LIDAR_PORT="$port"

  if [ ! -e "$port" ]; then
    echo "[lidar-motor] CHYBA: seriovy port '$port' neexistuje (nastav LIDAR_PORT=<port>)." >&2
    return 1
  fi

  local -a run_cmd
  if [ "$(id -u)" -ne 0 ] && { [ ! -r "$port" ] || [ ! -w "$port" ]; }; then
    echo "[lidar-motor] Nemam prava k $port ($(stat -c '%A %U:%G' "$port" 2>/dev/null || echo 'neznamy vlastnik'))." >&2
    echo "[lidar-motor] Trvale reseni: sudo usermod -aG dialout $USER  # potom odhlasit/prihlasit" >&2
    if command -v sudo >/dev/null 2>&1; then
      echo "[lidar-motor] Zkousim jednorazove sudo..." >&2
      run_cmd=(sudo env "LIDAR_PORT=$port" "$bin" "$cmd" serial)
    else
      return 1
    fi
  else
    run_cmd=("$bin" "$cmd" serial)
  fi

  local limit="${LIDAR_MOTOR_SERIAL_TIMEOUT:-8}"
  echo "[lidar-motor] $cmd pres serial $port (timeout ${limit}s)"
  set +e
  timeout "$limit" "${run_cmd[@]}"
  local rc=$?
  set -e
  if [ "$rc" -eq 124 ]; then
    echo "[lidar-motor] Serial neodpovedel do ${limit}s." >&2
  fi
  return "$rc"
}

lidar_find_iface() {
  if [ -n "${LIDAR_IFACE:-}" ]; then
    printf '%s\n' "$LIDAR_IFACE"
    return 0
  fi
  if ip link show eno1 >/dev/null 2>&1; then
    printf '%s\n' "eno1"
    return 0
  fi

  local defaults dev name
  defaults="$(ip route show default 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i=="dev") print $(i+1)}')"
  while IFS= read -r dev; do
    name="${dev%%@*}"
    [ "$name" = "lo" ] && continue
    printf '%s\n' "$defaults" | grep -qx "$name" && continue
    case "$name" in
      docker*|br-*|virbr*|veth*|tun*|tap*) continue ;;
    esac
    printf '%s\n' "$name"
    return 0
  done < <(ip -o link show | awk -F': ' '{print $2}')

  printf '%s\n' "eno1"
}

lidar_prepare_udp() {
  local iface
  iface="$(lidar_find_iface)"
  LIDAR_UDP_IFACE="$iface"
  local pc_ip="192.168.1.2/24"
  local lidar_ip="192.168.1.62"

  if ! command -v ip >/dev/null 2>&1; then
    echo "[lidar-motor] CHYBA: chybi prikaz 'ip' (iproute2)." >&2
    return 1
  fi
  if ! ip link show "$iface" >/dev/null 2>&1; then
    echo "[lidar-motor] CHYBA: rozhrani '$iface' neexistuje (nastav LIDAR_IFACE=<nic>)." >&2
    return 1
  fi
  if ip route show default 2>/dev/null | grep -qw "dev $iface"; then
    echo "[lidar-motor] STOP: '$iface' nese default route stroje - odmitam na nej sahat." >&2
    echo "[lidar-motor] Pouzij USB/serial, nebo nastav LIDAR_IFACE na samostatnou sitovku LiDARu." >&2
    return 1
  fi

  if ip -br addr show "$iface" 2>/dev/null | grep -q "192.168.1.2"; then
    echo "[lidar-motor] IP 192.168.1.2 uz je na $iface"
  else
    echo "[lidar-motor] Nastavuji $pc_ip na $iface (sudo)"
    sudo ip addr add "$pc_ip" dev "$iface"
  fi
  sudo ip link set "$iface" up

  if ping -c1 -W1 "$lidar_ip" >/dev/null 2>&1; then
    echo "[lidar-motor] LiDAR $lidar_ip odpovida na ping"
  else
    echo "[lidar-motor] POZOR: LiDAR $lidar_ip neodpovida na ping, prikaz presto zkusim." >&2
  fi
}

lidar_run_motor_udp() {
  local bin="$1" cmd="$2"
  lidar_prepare_udp || return $?

  local limit="${LIDAR_MOTOR_UDP_TIMEOUT:-8}"
  echo "[lidar-motor] $cmd pres ethernet/UDP na ${LIDAR_UDP_IFACE:-?} (timeout ${limit}s)"
  set +e
  timeout "$limit" "$bin" "$cmd" udp
  local rc=$?
  set -e
  if [ "$rc" -eq 124 ]; then
    echo "[lidar-motor] UDP neodpovedelo do ${limit}s." >&2
  fi
  return "$rc"
}

lidar_motor_usage() {
  cat >&2 <<'EOF'
Pouziti:
  ./lidar-quiet.sh [auto|serial|udp]
  ./lidar-wake.sh  [auto|serial|udp]

Default je auto: zkusi serialovy port (/dev/ttyACM*/ttyUSB*, nebo LIDAR_PORT) a pri
neuspechu UDP. Pro ethernet nastav pripadne LIDAR_IFACE=<nic>.
EOF
}

lidar_motor_main() {
  local bin="$1" cmd="$2" mode="${3:-${LIDAR_TRANSPORT:-auto}}"

  ulimit -c 0 || true

  if [ ! -x "$bin" ]; then
    echo "[lidar-motor] CHYBA: binarka '$bin' neexistuje nebo neni spustitelna (zkompiluj SDK)." >&2
    return 1
  fi

  case "$mode" in
    serial)
      lidar_run_motor_serial "$bin" "$cmd"
      ;;
    udp|ethernet|enet)
      lidar_run_motor_udp "$bin" "$cmd"
      ;;
    auto|"")
      local port rc
      port="$(lidar_find_serial_port)"
      if [ -e "$port" ]; then
        rc=0
        lidar_run_motor_serial "$bin" "$cmd" || rc=$?
        if [ "$rc" -eq 0 ]; then
          return 0
        fi
        echo "[lidar-motor] Serial neprosel (rc=$rc), zkousim ethernet/UDP..." >&2
      else
        echo "[lidar-motor] Serial port $port neexistuje, zkousim ethernet/UDP..." >&2
      fi
      lidar_run_motor_udp "$bin" "$cmd"
      ;;
    -h|--help|help)
      lidar_motor_usage
      return 0
      ;;
    *)
      echo "[lidar-motor] CHYBA: neznamy rezim '$mode'." >&2
      lidar_motor_usage
      return 2
      ;;
  esac
}
