#!/usr/bin/env bash
set -euo pipefail

echo "[apparmor] restoring profiles"

systemctl start apparmor
systemctl enable apparmor

apparmor_parser -r /etc/apparmor.d/*

echo "[apparmor] restore complete"
