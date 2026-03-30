#!/usr/bin/env bash
# Validates the full local Infinito.Nexus deploy flow from a clean state.
# Serves as a reference for how to deploy and debug applications locally.
set -euo pipefail

# Force local runtime context.
unset GITHUB_ACTIONS
unset ACT

# =============================================================================
# Configuration — apps and URLs used throughout this script.
# =============================================================================

# web-app-dashboard is chosen as the first deploy target because it is lightweight
# and has few dependencies, making it fast to deploy in CI and on minimal hardware.
# web-app-matomo is chosen as the second target because it has few dependencies
# and deploys quickly, making it ideal for environment validation.
DASHBOARD_APP="web-app-dashboard"
MATOMO_APP="web-app-matomo"
DASHBOARD_URL="https://dashboard.infinito.example"
MATOMO_URL="https://matomo.infinito.example"

# =============================================================================
# Script utilities — internal helpers required by this script only.
# =============================================================================

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# pkgmgr images may reset the working directory before invoking this script.
cd "${REPO_ROOT}"

# =============================================================================
# Install — install package prerequisites and repository dependencies.
# =============================================================================

# Install system-level package prerequisites for the repository toolchain.
bash "${REPO_ROOT}/scripts/install/package.sh"

echo "Installing Python tooling, Ansible collections, and all repository dependencies."
make install

# Load global environment (sets INVENTORY_DIR, INFINITO_DISTRO, etc.).
# shellcheck source=scripts/meta/env/all.sh
source "${REPO_ROOT}/scripts/meta/env/all.sh"

# =============================================================================
# System — show disk usage and purge cached state before building.
# =============================================================================

echo "Showing current disk and Docker resource usage before purging."
make system-disk-usage

echo "Freeing disk and memory on minimal-hardware systems before the build."
make system-purge

# =============================================================================
# Build — build the local Docker image and verify a clean no-cache build.
# =============================================================================

echo "Building the local image using the Docker layer cache."
make build

echo "Rebuilding the local image from scratch to verify the build without cache reuse."
make build-no-cache

# =============================================================================
# Bootstrap — install dependencies and prepare the environment for deployment.
# =============================================================================

echo "Bootstrapping the development environment: DNS, AppArmor, IPv6, and lint tooling."
make environment-bootstrap

echo "Starting the local compose stack (builds the image if missing)."
make up

# =============================================================================
# Testing — run the full validation suite before deploying.
# =============================================================================

echo "Running the combined validation suite: lint, unit tests, and integration tests."
make test

# =============================================================================
# Deploy on minimal hardware — disable non-essential services to save resources.
# =============================================================================

echo "Deploying dashboard with matomo disabled to verify SERVICES_DISABLED suppresses the shared service in the inventory."
SERVICES_DISABLED="matomo" make deploy-fresh-purged-apps APPS="${DASHBOARD_APP}"
inspect

echo "Trusting the local CA certificate so HTTPS endpoints are reachable from the host."
make trust-ca

echo "Verifying the dashboard is reachable (matomo was disabled, not the dashboard itself)."
assert_http_status 200 "${DASHBOARD_URL}"

echo "Verifying matomo is not reachable because it was excluded from the inventory."
# curl returns 000 (no HTTP response) instead of 404 because the TLS handshake
# fails first: matomo's subdomain is not listed as a SAN in the deployed
# certificate, so curl aborts before any HTTP exchange takes place.
assert_http_status 000 "${MATOMO_URL}"

# =============================================================================
# Deploy on performance hardware — deploy the full set of applications.
# =============================================================================

echo "Deploying matomo (full cycle: deploy + update pass) so it becomes reachable via its dedicated inventory entry."
FULL_CYCLE=true make deploy-fresh-purged-apps APPS="${MATOMO_APP}"
inspect

echo "Re-trusting the CA after the fresh deploy rebuilt the certificates."
make trust-ca

echo "Verifying matomo is now reachable after its dedicated deploy."
assert_http_status 200 "${MATOMO_URL}"

echo "Verifying the dashboard is no longer reachable after the matomo-only fresh deploy."
# curl returns 000 (no HTTP response) instead of 404 because the fresh deploy
# rebuilt the certificate for matomo only, so dashboard's subdomain is no
# longer a SAN — the TLS handshake fails before any HTTP exchange takes place.
assert_http_status 000 "${DASHBOARD_URL}"

# =============================================================================
# Redeploy keeping inventory and apt packages — validates reuse of existing state.
# =============================================================================

echo "Redeploying matomo while keeping inventory and packages to validate state reuse."
make deploy-reuse-kept-apps APPS="${MATOMO_APP}"
inspect

# =============================================================================
# Teardown — shut down the stack and reverse all environment changes.
# =============================================================================

echo "Stopping the compose stack and removing all volumes for a clean teardown."
make down

echo "Reversing the environment bootstrap (DNS, AppArmor, IPv6 settings)."
make environment-teardown
