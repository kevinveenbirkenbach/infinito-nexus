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

# Snapshot cache request counters. Outputs `<nexus_lines> <registry_hits>`.
cache_snapshot() {
	local nexus_lines registry_hits
	nexus_lines="$(docker exec infinito-package-cache sh -c 'wc -l </nexus-data/log/request.log' 2>/dev/null | awk '{print $1}')"
	registry_hits="$(docker logs infinito-registry-cache 2>&1 | grep -c '"upstream_cache_status":"HIT"' || true)"
	printf '%s %s\n' "${nexus_lines:-0}" "${registry_hits:-0}"
}

# Assert that cache traffic grew between two snapshots.
# Usage: assert_cache_used <before> <after>  (both as `<nexus> <registry>` pairs)
assert_cache_used() {
	local before="${1}" after="${2}"
	local nexus_before registry_before nexus_after registry_after
	read -r nexus_before registry_before <<<"${before}"
	read -r nexus_after registry_after <<<"${after}"
	local delta_nexus=$((nexus_after - nexus_before))
	local delta_registry=$((registry_after - registry_before))
	echo "[cache] nexus requests +${delta_nexus} (was ${nexus_before}, now ${nexus_after})"
	echo "[cache] registry HITs   +${delta_registry} (was ${registry_before}, now ${registry_after})"
	if [[ "${delta_nexus}" -le 0 && "${delta_registry}" -le 0 ]]; then
		echo "[FAIL] no cache traffic observed during deploy" >&2
		exit 1
	fi
	echo "[OK] cache observed activity during deploy"
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
