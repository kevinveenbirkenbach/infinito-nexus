#!/usr/bin/env bash
# Shared variables and helpers for the environment test suite.
set -euo pipefail

DASHBOARD_APP="web-app-dashboard"
MATOMO_APP="web-app-matomo"
DASHBOARD_URL="https://dashboard.infinito.example"
MATOMO_URL="https://matomo.infinito.example"

# These constants are part of the sourced interface consumed by sibling scripts.
: "${DASHBOARD_APP}" "${MATOMO_APP}" "${DASHBOARD_URL}" "${MATOMO_URL}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

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
inspect() {
	echo "Printing the generated inventory to verify which roles were deployed."
	make exec CMD="cat ${INVENTORY_FILE}"
	echo "Printing host_vars to verify per-host configuration."
	make exec CMD="cat ${HOST_VARS_FILE}"
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
