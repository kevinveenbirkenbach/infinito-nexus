#!/usr/bin/env bash
# Validates the full local Infinito.Nexus deploy flow from a clean state.
# Serves as a reference for how to deploy and debug applications locally.
set -euo pipefail

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

# Load global environment (sets INVENTORY_DIR, INFINITO_DISTRO, etc.).
# shellcheck source=scripts/meta/env/all.sh
source "${REPO_ROOT}/scripts/meta/env/all.sh"

# =============================================================================
# Install — install package prerequisites and repository dependencies.
# =============================================================================

# Install system-level package prerequisites for the repository toolchain.
bash "${REPO_ROOT}/scripts/install/package.sh"

# Install Python tooling, Ansible collections, and all repository dependencies.
make install

# =============================================================================
# Build — build the local Docker image and verify a clean no-cache build.
# =============================================================================

# Build the local image using the Docker layer cache.
make build

# Rebuild the local image from scratch to verify the build without cache reuse.
make build-no-cache

# =============================================================================
# System — show disk usage and purge cached state before building.
# =============================================================================

# Show current disk and Docker resource usage before purging.
make system-disk-usage

# Required on minimal-hardware systems to free disk and memory before the build.
make system-purge

# =============================================================================
# Bootstrap — install dependencies and prepare the environment for deployment.
# =============================================================================

# Bootstrap the development environment: DNS, AppArmor, IPv6, and lint tooling.
make environment-bootstrap

# Start the local compose stack (builds the image if missing).
make up

# =============================================================================
# Testing — run the full validation suite before deploying.
# =============================================================================

# Run the combined validation suite: lint, unit tests, and integration tests.
make test

# =============================================================================
# Deploy on minimal hardware — disable non-essential services to save resources.
# =============================================================================

# Deploy dashboard with matomo disabled to verify that SERVICES_DISABLED suppresses
# the shared service in the generated inventory.
SERVICES_DISABLED="matomo" make deploy-fresh-purged-apps APPS="${DASHBOARD_APP}"

# Verify that the generated inventory does not contain the disabled service provider.
if make exec CMD="grep -q '${MATOMO_APP}' ${INVENTORY_DIR}/devices.yml" 2>/dev/null; then
	echo "[FAIL] ${MATOMO_APP} found in inventory after SERVICES_DISABLED=matomo" >&2
	exit 1
fi
echo "[OK] ${MATOMO_APP} is absent from inventory"

# Trust the local CA certificate so HTTPS endpoints are reachable from the host.
make trust-ca

# Verify the dashboard is reachable (matomo was disabled, not the dashboard itself).
assert_http_status 200 "${DASHBOARD_URL}"

# Verify matomo is not reachable because it was excluded from the inventory.
# The nginx proxy returns 404 when no upstream is configured for this host.
assert_http_status 404 "${MATOMO_URL}"

# =============================================================================
# Deploy on performance hardware — deploy the full set of applications.
# =============================================================================

# Deploy matomo so it becomes reachable via its dedicated inventory entry.
make deploy-fresh-purged-apps APPS="${MATOMO_APP}"

# Re-trust the CA after the fresh deploy rebuilt the certificates.
make trust-ca

# Verify matomo is now reachable after its dedicated deploy.
assert_http_status 200 "${MATOMO_URL}"

# Verify the dashboard is no longer reachable. deploy-fresh-purged-apps purges the
# previous inventory and containers before deploying, so web-app-dashboard is gone
# after the matomo-only deploy. nginx returns 404 for unconfigured upstreams.
assert_http_status 404 "${DASHBOARD_URL}"

# =============================================================================
# Redeploy keeping inventory and apt packages — validates reuse of existing state.
# =============================================================================

make deploy-reuse-kept-apps APPS="${MATOMO_APP}"

# =============================================================================
# Teardown — shut down the stack and reverse all environment changes.
# =============================================================================

# Stop the compose stack and remove all volumes for a clean teardown.
make down

# Reverse the environment bootstrap (DNS, AppArmor, IPv6 settings).
make environment-teardown
