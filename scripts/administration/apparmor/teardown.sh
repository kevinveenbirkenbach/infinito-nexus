#!/usr/bin/env bash
set -euo pipefail

echo "[apparmor] tearing down (dev mode)"

systemctl stop apparmor || true

if command -v aa-teardown >/dev/null 2>&1; then
  aa-teardown
else
  apparmor_parser -R /etc/apparmor.d/* || true
fi

echo "[apparmor] teardown complete"
