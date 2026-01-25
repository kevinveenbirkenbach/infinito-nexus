#!/usr/bin/env bash
set -euo pipefail

# 1) systemd private socket must exist
if [[ ! -S /run/systemd/private ]]; then
  echo "systemd socket not ready"
  exit 1
fi

# 2) systemd must be running or degraded
state="$(systemctl is-system-running --wait 2>/dev/null || true)"

case "$state" in
  running|degraded)
    ;;
  *)
    echo "systemd state: $state"
    exit 1
    ;;
esac

# 3) infinito command must exist and be executable
if ! command -v infinito >/dev/null 2>&1; then
  echo "infinito command not found"
  exit 1
fi

if [[ ! -x "$(command -v infinito)" ]]; then
  echo "infinito command not executable"
  exit 1
fi

# 4) infinito must return 0 (smoke test)
if ! infinito --help >/dev/null 2>&1; then
  echo "infinito command failed"
  exit 1
fi

# all good
exit 0
