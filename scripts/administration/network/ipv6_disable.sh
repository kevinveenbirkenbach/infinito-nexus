#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="/tmp/infinito-dev-environment"
STATE_FILE="${STATE_DIR}/ipv6.state"

skip_ipv6_disable() {
	echo "[ipv6] skipping disable: $*"
	exit 0
}

read_ipv6_value() {
	local key="$1"
	sysctl -n "${key}" 2>/dev/null
}

write_state_once() {
	local current_all="$1"
	local current_default="$2"

	if [[ -f "${STATE_FILE}" ]]; then
		echo "[ipv6] existing state file found at ${STATE_FILE}; keeping original restore values"
		return 0
	fi

	install -d "${STATE_DIR}"
	cat >"${STATE_FILE}" <<EOF
ALL_DISABLE_IPV6=${current_all}
DEFAULT_DISABLE_IPV6=${current_default}
EOF
}

remove_state_file() {
	rm -f "${STATE_FILE}"
	rmdir "${STATE_DIR}" 2>/dev/null || true
}

if ! command -v sysctl >/dev/null 2>&1; then
	skip_ipv6_disable "sysctl is unavailable in this environment"
fi

current_all="$(read_ipv6_value net.ipv6.conf.all.disable_ipv6)" || skip_ipv6_disable "kernel does not expose net.ipv6.conf.all.disable_ipv6"
current_default="$(read_ipv6_value net.ipv6.conf.default.disable_ipv6)" || skip_ipv6_disable "kernel does not expose net.ipv6.conf.default.disable_ipv6"

echo "[ipv6] current: all=${current_all} default=${current_default}"
write_state_once "${current_all}" "${current_default}"

if ! sysctl -w net.ipv6.conf.all.disable_ipv6=1; then
	remove_state_file
	skip_ipv6_disable "cannot update net.ipv6.conf.all.disable_ipv6"
fi

if ! sysctl -w net.ipv6.conf.default.disable_ipv6=1; then
	sysctl -w "net.ipv6.conf.all.disable_ipv6=${current_all}" >/dev/null 2>&1 || true
	remove_state_file
	skip_ipv6_disable "cannot update net.ipv6.conf.default.disable_ipv6"
fi

echo "[ipv6] disabled"
