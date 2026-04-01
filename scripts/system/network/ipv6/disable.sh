#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="/tmp/infinito-dev-environment-ipv6.state"

if ! command -v sysctl >/dev/null 2>&1; then
	echo "[ipv6] skipping disable: sysctl is unavailable in this environment"
	exit 0
fi

if ! current_all="$(sysctl -n net.ipv6.conf.all.disable_ipv6 2>/dev/null)"; then
	echo "[ipv6] skipping disable: kernel does not expose net.ipv6.conf.all.disable_ipv6"
	exit 0
fi

if ! current_default="$(sysctl -n net.ipv6.conf.default.disable_ipv6 2>/dev/null)"; then
	echo "[ipv6] skipping disable: kernel does not expose net.ipv6.conf.default.disable_ipv6"
	exit 0
fi

echo "[ipv6] current: all=${current_all} default=${current_default}"

if [[ ! -f "${STATE_FILE}" ]]; then
	cat >"${STATE_FILE}" <<EOF
ALL_DISABLE_IPV6=${current_all}
DEFAULT_DISABLE_IPV6=${current_default}
EOF
else
	echo "[ipv6] existing state file found at ${STATE_FILE}; keeping original restore values"
fi

if ! sysctl -w net.ipv6.conf.all.disable_ipv6=1 >/dev/null; then
	rm -f "${STATE_FILE}"
	echo "[ipv6] skipping disable: cannot update net.ipv6.conf.all.disable_ipv6"
	exit 0
fi

if ! sysctl -w net.ipv6.conf.default.disable_ipv6=1 >/dev/null; then
	if ! sysctl -w "net.ipv6.conf.all.disable_ipv6=${current_all}" >/dev/null 2>&1; then
		echo "[ipv6] warning: failed to restore net.ipv6.conf.all.disable_ipv6"
	fi
	rm -f "${STATE_FILE}"
	echo "[ipv6] skipping disable: cannot update net.ipv6.conf.default.disable_ipv6"
	exit 0
fi

echo "[ipv6] disabled"
