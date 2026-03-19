#!/usr/bin/env bash
set -euo pipefail

# Skip gracefully when AppArmor is not installed or not enabled in this environment
if ! command -v apparmor_parser >/dev/null 2>&1; then
  echo "[apparmor] apparmor_parser not found — skipping restore"
  exit 0
fi

echo "[apparmor] restoring profiles"

systemctl start apparmor
systemctl enable apparmor

apparmor_parser -r /etc/apparmor.d/*

echo "[apparmor] restore complete"
