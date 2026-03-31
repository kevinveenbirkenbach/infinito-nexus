#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
stack_was_running=0

if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' 2>/dev/null | grep -Eq '^infinito_nexus_'; then
	stack_was_running=1
fi

sudo bash "${SCRIPT_DIR}/disable.sh"

if [[ "${stack_was_running}" -ne 1 ]]; then
	echo "[ipv6] no running Infinito dev stack detected; skipping stack recreate"
	exit 0
fi

echo "[ipv6] recreating running Infinito dev stack after IPv6 disable"
make -C "${REPO_ROOT}" down
make -C "${REPO_ROOT}" up
