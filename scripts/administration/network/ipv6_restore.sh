#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="/tmp/infinito-dev-environment"
STATE_FILE="${STATE_DIR}/ipv6.state"

skip_ipv6_restore() {
	echo "[ipv6] skipping restore: $*"
	exit 0
}

if [[ ! -f "${STATE_FILE}" ]]; then
	echo "[ipv6] no saved state found; skipping restore"
	exit 0
fi

# shellcheck disable=SC1090
source "${STATE_FILE}"

: "${ALL_DISABLE_IPV6:?Missing ALL_DISABLE_IPV6 in ${STATE_FILE}}"
: "${DEFAULT_DISABLE_IPV6:?Missing DEFAULT_DISABLE_IPV6 in ${STATE_FILE}}"

if ! command -v sysctl >/dev/null 2>&1; then
	skip_ipv6_restore "sysctl is unavailable in this environment"
fi

echo "[ipv6] restoring: all=${ALL_DISABLE_IPV6} default=${DEFAULT_DISABLE_IPV6}"

if ! sysctl -w "net.ipv6.conf.all.disable_ipv6=${ALL_DISABLE_IPV6}"; then
	skip_ipv6_restore "cannot update net.ipv6.conf.all.disable_ipv6"
fi

if ! sysctl -w "net.ipv6.conf.default.disable_ipv6=${DEFAULT_DISABLE_IPV6}"; then
	skip_ipv6_restore "cannot update net.ipv6.conf.default.disable_ipv6"
fi

rm -f "${STATE_FILE}"
rmdir "${STATE_DIR}" 2>/dev/null || true

echo "[ipv6] restore complete"
