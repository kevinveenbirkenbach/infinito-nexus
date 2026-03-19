#!/usr/bin/env bash
set -euo pipefail

# Skip gracefully when AppArmor module is not loaded in this environment
if ! grep -q '^[Yy1]' /sys/module/apparmor/parameters/enabled 2>/dev/null; then
  echo "[apparmor] AppArmor module is not loaded — skipping teardown"
  exit 0
fi

echo "[apparmor] tearing down (dev mode)"

systemctl stop apparmor || true

if command -v aa-teardown >/dev/null 2>&1; then
  aa-teardown
else
  apparmor_parser -R /etc/apparmor.d/* || true
fi

echo "[apparmor] teardown complete"
