#!/usr/bin/env bash
set -euo pipefail

echo "[docker-infinito] Starting package-manager container"

# ---------------------------------------------------------------------------
# Log distribution info
# ---------------------------------------------------------------------------
if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  echo "[docker-infinito] Detected distro: ${ID:-unknown} (like: ${ID_LIKE:-})"
fi

# ---------------------------------------------------------------------------
# DEV mode: rebuild package-manager from the mounted /opt/src/infinito tree
# ---------------------------------------------------------------------------
if [[ "${REINSTALL_INFINITO:-0}" == "1" ]]; then
  echo "[docker-infinito] Using /opt/src/infinito as working directory"
  cd /opt/src/infinito
  echo "[docker-infinito] DEV mode enabled (REINSTALL_INFINITO=1)"
  echo "[docker-infinito] Git safety: fix "detected dubious ownership" on bind mounts"
  git config --global --add safe.directory /opt/src/infinito || true
  echo "[docker-infinito] Reinstall via 'make install'..."
  make install || exit 1
fi

# ---------------------------------------------------------------------------
# Hand off to infinito or arbitrary command
# ---------------------------------------------------------------------------
if [[ $# -eq 0 ]]; then
  echo "[docker-infinito] No arguments provided. Showing infinito help..."
  exec infinito --help
else
  echo "[docker-infinito] Executing command: $*"
  exec "$@"
fi
