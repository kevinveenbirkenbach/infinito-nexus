#!/usr/bin/env bash
set -euo pipefail

echo "[docker-infinito] Starting infinito container"

# Compute dynamically if not provided from outside
INFINITO_PATH="$(pkgmgr path infinito)"
INFINITO_SRC_DIR="/opt/src/infinito"
export INFINITO_PATH
export INFINITO_SRC_DIR

# ---------------------------------------------------------------------------
# DEV mode: rebuild infinito
# ---------------------------------------------------------------------------
if [[ "${INSTALL_LOCAL_BUILD:-0}" == "1" ]]; then
	echo "[docker-infinito] Build enabled (INSTALL_LOCAL_BUILD=1)"
	echo "[docker-infinito] Using ${INFINITO_PATH} as working directory"
	mkdir -p "${INFINITO_PATH}"
	cd "${INFINITO_PATH}"
	echo "[docker-infinito] Copy ${INFINITO_SRC_DIR} to ${INFINITO_PATH}..."
	rsync -a --delete --exclude='.git' "${INFINITO_SRC_DIR}/" "${INFINITO_PATH}/"
	echo "[docker-infinito] Reinstall via 'make install'..."
	make install || exit 1
	echo "[docker-infinito] Installed:"
	pkgmgr version infinito
fi

# ---------------------------------------------------------------------------
# Hand off to infinito or arbitrary command
# ---------------------------------------------------------------------------
if [[ $# -eq 0 ]]; then
	echo "[docker-infinito] No arguments provided. Showing infinito help..."
	exec infinito --help
else
	cd "${INFINITO_PATH}"
	exec "$@"
fi
