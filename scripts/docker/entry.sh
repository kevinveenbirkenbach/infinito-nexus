#!/usr/bin/env bash
set -euo pipefail
echo "[docker-infinito] Starting infinito container"

# Compute dynamically if not provided from outside
echo "[docker-infinito] before pkgmgr path"
INFINITO_PATH="$(pkgmgr path infinito)"
echo "[docker-infinito] after pkgmgr path: ${INFINITO_PATH}"

INFINITO_SRC_DIR="/opt/src/infinito"
export INFINITO_PATH
export INFINITO_SRC_DIR

run_local_build() {
	echo "[docker-infinito] Build enabled (INSTALL_LOCAL_BUILD=1)"
	echo "[docker-infinito] Using ${INFINITO_PATH} as working directory"

	mkdir -p "${INFINITO_PATH}"
	cd "${INFINITO_PATH}"

	echo "[docker-infinito] Copy ${INFINITO_SRC_DIR} to ${INFINITO_PATH}..."
	rsync -a --delete --chown=root:root --exclude='.git' "${INFINITO_SRC_DIR}/" "${INFINITO_PATH}/"

	echo "[docker-infinito] Reinstall via 'make install'..."
	make install

	echo "[docker-infinito] Installed:"
	pkgmgr version infinito
}

# ---------------------------------------------------------------------------
# DEV mode: rebuild infinito
# ---------------------------------------------------------------------------
if [[ "${INSTALL_LOCAL_BUILD:-0}" == "1" ]]; then
	if [[ "${INSTALL_LOCAL_BUILD_SILENCE:-0}" == "1" ]]; then
		run_local_build >/dev/null 2>&1
	else
		run_local_build
	fi
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
