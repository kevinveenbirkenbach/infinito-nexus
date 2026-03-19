#!/usr/bin/env bash
set -euo pipefail

# Skip gracefully when AppArmor module is not loaded in this environment
if ! grep -q '^[Yy1]' /sys/module/apparmor/parameters/enabled 2>/dev/null; then
  echo "[apparmor] AppArmor module is not loaded — skipping restore"
  exit 0
fi

echo "[apparmor] restoring profiles"

systemctl start apparmor
systemctl enable apparmor

apparmor_parser -r /etc/apparmor.d/*

echo "[apparmor] restore complete"
