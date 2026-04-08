#!/usr/bin/env bash
# Shared variables and helpers for the environment test suite.
set -euo pipefail

DASHBOARD_APP="web-app-dashboard"
MATOMO_APP="web-app-matomo"
DASHBOARD_URL="https://dashboard.infinito.example"
MATOMO_URL="https://matomo.infinito.example"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

load_repo_env() {
	local previous_pwd
	previous_pwd="$(pwd)"
	cd "${REPO_ROOT}"
	# shellcheck source=scripts/meta/env/all.sh
	source scripts/meta/env/all.sh
	cd "${previous_pwd}"
}

load_repo_env

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
