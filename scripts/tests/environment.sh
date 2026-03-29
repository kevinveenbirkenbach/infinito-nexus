#!/usr/bin/env bash
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

# Install system-level package prerequisites for the repository toolchain.
bash "${REPO_ROOT}/scripts/install/package.sh"

# =============================================================================
# Local test deployment — demonstrates how to deploy and verify Infinito.Nexus
# locally. The steps below serve as a reference for debugging and manual
# validation: they show the exact sequence used to bring up a clean environment,
# deploy individual applications, and confirm they are reachable via HTTPS.
# =============================================================================

# =============================================================================
# Bootstrap — prepare the environment from scratch before running deployments.
# =============================================================================

# Purge all local state: container inventory, Docker images, and system caches.
# Primarily intended for minimal-hardware environments where disk and memory
# are scarce — frees space before the install and deploy cycle begins.
# Also simulates a fully clean environment so the full flow is validated
# without relying on any cached state from a previous run.
make purge-all

# Install Python tooling, Ansible collections, and all repository dependencies.
make install

# Bootstrap the development environment: DNS, AppArmor, IPv6, and lint tooling.
make environment-bootstrap

# Start the local compose stack (builds the image if missing).
make up

# Run the combined validation suite: lint, unit tests, and integration tests.
make test

# Deploy dashboard with matomo disabled to verify that SERVICES_DISABLED suppresses
# the shared service in the generated inventory.
SERVICES_DISABLED="matomo" make deploy-fresh-purged-app APPS="${DASHBOARD_APP}"

# Trust the local CA certificate so HTTPS endpoints are reachable from the host.
make trust-ca

# Verify the dashboard is reachable (matomo was disabled, not the dashboard itself).
assert_http_status 200 "${DASHBOARD_URL}"

# Verify matomo is not reachable because it was excluded from the inventory.
# The nginx proxy returns 404 when no upstream is configured for this host.
assert_http_status 404 "${MATOMO_URL}"

# Deploy matomo so it becomes reachable via its dedicated inventory entry.
make deploy-fresh-purged-app APPS="${MATOMO_APP}"

# Re-trust the CA after the fresh deploy rebuilt the certificates.
make trust-ca

# Verify matomo is now reachable after its dedicated deploy.
assert_http_status 200 "${MATOMO_URL}"

# Verify the dashboard is no longer reachable. deploy-fresh-purged-app purges the
# previous inventory and containers before deploying, so web-app-dashboard is gone
# after the matomo-only deploy. nginx returns 404 for unconfigured upstreams.
assert_http_status 404 "${DASHBOARD_URL}"

# =============================================================================
# Teardown — shut down the stack and reverse all environment changes.
# =============================================================================

# Stop the compose stack and remove all volumes for a clean teardown.
make down

# Reverse the environment bootstrap (DNS, AppArmor, IPv6 settings).
make environment-teardown
