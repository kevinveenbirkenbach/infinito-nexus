#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="/tmp/infinito-dev-environment-ipv6.state"

if [[ ! -f "${STATE_FILE}" ]]; then
	echo "[ipv6] no saved state found; skipping restore"
	exit 0
fi

if ! command -v sysctl >/dev/null 2>&1; then
	echo "[ipv6] skipping restore: sysctl is unavailable in this environment"
	exit 0
fi

# shellcheck disable=SC1090
source "${STATE_FILE}"

: "${ALL_DISABLE_IPV6:?Missing ALL_DISABLE_IPV6 in ${STATE_FILE}}"
: "${DEFAULT_DISABLE_IPV6:?Missing DEFAULT_DISABLE_IPV6 in ${STATE_FILE}}"

echo "[ipv6] restoring: all=${ALL_DISABLE_IPV6} default=${DEFAULT_DISABLE_IPV6}"

if ! sysctl -w "net.ipv6.conf.all.disable_ipv6=${ALL_DISABLE_IPV6}" >/dev/null; then
	echo "[ipv6] skipping restore: cannot update net.ipv6.conf.all.disable_ipv6"
	exit 0
fi

if ! sysctl -w "net.ipv6.conf.default.disable_ipv6=${DEFAULT_DISABLE_IPV6}" >/dev/null; then
	echo "[ipv6] skipping restore: cannot update net.ipv6.conf.default.disable_ipv6"
	exit 0
fi

rm -f "${STATE_FILE}"

echo "[ipv6] restore complete"
