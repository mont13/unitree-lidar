#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Docasne BEZHESLOVE sudo pro uzivatele (kvuli instalaci/sit. nastaveni
# pri rozjezdu LiDARu). Automaticky se odebere po 4 hodinach.
#
# Spust JEDNOU s heslem (cesta $DIR = adresar tohoto skriptu):
#     sudo bash "$DIR/setup-temp-sudo.sh"
#
# Rucni zruseni kdykoli:
#     sudo bash "$DIR/remove-temp-sudo.sh"
# ---------------------------------------------------------------------------
set -euo pipefail

# Koren odvozen ze samotneho skriptu (zadne hardcoded cesty)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Uzivatel: 1. argument, jinak SUDO_USER (kdo spustil sudo), jinak prihlaseny uzivatel
USER_NAME=${1:-${SUDO_USER:-$(logname 2>/dev/null)}}
SUDO_FILE="/etc/sudoers.d/claude-temp-4h"

if [ "$(id -u)" -ne 0 ]; then
  echo "Tento skript spust pres sudo:  sudo bash $0" >&2
  exit 1
fi

if [ -z "${USER_NAME}" ]; then
  echo "CHYBA: nepodarilo se zjistit uzivatele. Zadej ho jako argument:  sudo bash $0 <uzivatel>" >&2
  exit 1
fi

# 1) Vytvor docasne NOPASSWD pravidlo
echo "${USER_NAME} ALL=(ALL) NOPASSWD:ALL" > "${SUDO_FILE}"
chmod 0440 "${SUDO_FILE}"

# 2) Over syntaxi sudoers; pri chybe pravidlo zase smaz
if ! visudo -cf "${SUDO_FILE}" >/dev/null; then
  rm -f "${SUDO_FILE}"
  echo "CHYBA: validace sudoers selhala, pravidlo odebrano." >&2
  exit 1
fi

# 3) Naplanuj automaticke odebrani za 4 hodiny
if command -v systemd-run >/dev/null 2>&1; then
  systemctl stop claude-temp-sudo-cleanup.timer 2>/dev/null || true
  systemd-run --on-active=4h --unit=claude-temp-sudo-cleanup \
    /bin/rm -f "${SUDO_FILE}" >/dev/null 2>&1
  echo "Auto-odebrani naplanovano (systemd timer: claude-temp-sudo-cleanup)."
else
  nohup bash -c "sleep 14400; rm -f '${SUDO_FILE}'" >/dev/null 2>&1 &
  echo "Auto-odebrani naplanovano (background sleep, nezustane po restartu PC)."
fi

echo "OK: docasne bezheslove sudo pro '${USER_NAME}' je aktivni."
echo "    Plati do: $(date -d '+4 hours' '+%H:%M  %d.%m.%Y')"
echo "    Rucni zruseni: sudo bash ${DIR}/remove-temp-sudo.sh"
echo "    Pozor: pri restartu PC behem teto doby pravidlo nemusi vyprset samo -> v tom pripade zrus rucne."
