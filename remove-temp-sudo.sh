#!/usr/bin/env bash
# Okamzite zruseni docasneho bezhesloveho sudo (viz setup-temp-sudo.sh).
#     sudo bash "$DIR/remove-temp-sudo.sh"   (DIR = adresar tohoto skriptu)
set -euo pipefail

# koren odvozeny ze samotneho skriptu (zadna hardcoded cesta)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "Spust pres sudo:  sudo bash $DIR/$(basename "$0")" >&2
  exit 1
fi

rm -f /etc/sudoers.d/claude-temp-4h
systemctl stop claude-temp-sudo-cleanup.timer 2>/dev/null || true
systemctl reset-failed claude-temp-sudo-cleanup.timer 2>/dev/null || true
echo "Docasne bezheslove sudo bylo odebrano."
