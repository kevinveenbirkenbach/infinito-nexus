#!/usr/bin/env bash
set -euo pipefail

PROFILES=(
  /etc/apparmor.d/php-fpm
  /etc/apparmor.d/usr.sbin.dovecot
  /etc/apparmor.d/usr.lib.dovecot.*
)

echo "[apparmor] setting profiles to complain mode (dev host)"

for profile in "${PROFILES[@]}"; do
  for resolved in $profile; do
    if [[ -e "$resolved" ]]; then
      echo " -> aa-complain $resolved"
      aa-complain "$resolved" || true
    else
      echo " -> skip $resolved (not found)"
    fi
  done
done

echo "[apparmor] done"
