#!/usr/bin/env bash
# Shared bootstrap, constants, and generic helpers for the environment
# test suite. Sourcing this file loads the repository env modules and
# configures git's safe.directory for the mounted workflow checkout.
# Cache-specific helpers live in cache.sh.
set -euo pipefail

DASHBOARD_APP="web-app-dashboard"
MATOMO_APP="web-app-matomo"
DASHBOARD_URL="https://dashboard.infinito.example"
MATOMO_URL="https://matomo.infinito.example"

# These constants are part of the sourced interface consumed by sibling scripts.
: "${DASHBOARD_APP}" "${MATOMO_APP}" "${DASHBOARD_URL}" "${MATOMO_URL}"

UTILS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${UTILS_DIR}/../../../.." && pwd)"

ensure_git_safe_directory() {
	local git_probe=""

	if ! command -v git >/dev/null 2>&1; then
		return 0
	fi

	if git -C "${REPO_ROOT}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
		return 0
	fi

	git_probe="$(git -C "${REPO_ROOT}" rev-parse --is-inside-work-tree 2>&1 || true)"
	if [[ "${git_probe}" != *"detected dubious ownership"* ]]; then
		return 0
	fi

	if ! git config --global --get-all safe.directory 2>/dev/null | grep -Fx "${REPO_ROOT}" >/dev/null 2>&1; then
		echo "Configuring Git safe.directory for the mounted workflow checkout."
		git config --global --add safe.directory "${REPO_ROOT}"
	fi
}

load_repo_env() {
	local previous_pwd
	previous_pwd="$(pwd)"
	cd "${REPO_ROOT}"
	unset INFINITO_ENV_LOADED
	unset INFINITO_ENV_PYTHON_LOADED
	unset INFINITO_ENV_RUNTIME_LOADED
	unset INFINITO_ENV_DEFAULTS_LOADED
	unset INFINITO_ENV_INVENTORY_LOADED
	unset INFINITO_ENV_GITHUB_LOADED
	unset PYTHON
	unset PIP
	# shellcheck source=scripts/meta/env/all.sh
	source scripts/meta/env/all.sh
	cd "${previous_pwd}"
}

load_repo_env
ensure_git_safe_directory

# Print the generated inventory and host_vars for debugging and verification.
#
# Matrix-variant deploys write `${INVENTORY_DIR}-0/devices.yml`,
# `${INVENTORY_DIR}-1/devices.yml`, ... never the unsuffixed
# `${INVENTORY_DIR}/devices.yml`. Discover every variant inside the
# infinito_nexus container (where the inventories actually live) and
# print each one; fall back to the unsuffixed path when no variants
# exist.
#
# CMD is executed via `sh -lc` (see scripts/tests/deploy/local/exec/container.sh)
# — keep the inner shell strictly POSIX (no bash arrays, no `shopt`, no `(( ))`).
inspect_glob_print() {
	local glob_pattern="$1" fallback="$2"
	make exec CMD="set -eu; \
		any=; \
		for f in ${glob_pattern}; do \
			[ -f \"\$f\" ] || continue; \
			any=1; \
			printf '==> %s\\n' \"\$f\"; \
			cat \"\$f\"; \
		done; \
		if [ -z \"\$any\" ]; then \
			printf '==> %s\\n' \"${fallback}\"; \
			cat \"${fallback}\"; \
		fi"
}

inspect() {
	echo "Printing the generated inventory to verify which roles were deployed."
	inspect_glob_print "${INVENTORY_DIR}-*/devices.yml" "${INVENTORY_FILE}"
	echo "Printing host_vars to verify per-host configuration."
	inspect_glob_print "${INVENTORY_DIR}-*/host_vars/localhost.yml" "${HOST_VARS_FILE}"
}

# Check that a URL responds with the expected HTTP status code.
# Usage: assert_http_status <expected_code> <url>
assert_http_status() {
	local expected="${1}"
	local url="${2}"
	local actual
	actual="$(curl -sS -o /dev/null -w '%{http_code}' "${url}" || true)"
	if [ "${actual}" != "${expected}" ]; then
		echo "[FAIL] ${url} returned HTTP ${actual}, expected ${expected}" >&2
		exit 1
	fi
	echo "[OK] ${url} returned HTTP ${actual}"
}
