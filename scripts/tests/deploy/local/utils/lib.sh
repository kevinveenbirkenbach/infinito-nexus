#!/usr/bin/env bash
set -euo pipefail

# Shared helpers for local deploy test scripts.

normalize_bool() {
	case "${1:-}" in
	true | True | TRUE | 1) printf '%s\n' "true" ;;
	false | False | FALSE | 0 | "") printf '%s\n' "false" ;;
	*)
		return 1
		;;
	esac
}

normalize_bool_or_default() {
	local value="${1:-}"
	local default="${2:?default boolean value is required}"
	local label="${3:-value}"
	local normalized

	if [[ -z "${value}" ]]; then
		printf '%s\n' "${default}"
		return 0
	fi

	if normalized="$(normalize_bool "${value}")"; then
		printf '%s\n' "${normalized}"
	else
		echo "WARN: ignoring invalid ${label} value '${value}', using default ${default}" >&2
		printf '%s\n' "${default}"
	fi
}
