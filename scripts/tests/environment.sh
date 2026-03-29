#!/usr/bin/env bash
set -euo pipefail

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

# Purge all local state: container inventory, Docker images, and system caches.
# Simulates a fully cleaned environment before the install and deploy cycle.
# Use this to verify that the full flow works from scratch without relying on
# any cached state from a previous run.
make purge-all

# Install Python tooling, Ansible collections, and all repository dependencies.
make install

# Bootstrap the development environment: DNS, AppArmor, IPv6, and lint tooling.
make environment-bootstrap

# Start the local compose stack (builds the image if missing).
make up

# Run the combined validation suite: lint, unit tests, and integration tests.
make test

DASHBOARD_URL="https://dashboard.infinito.example"
MATOMO_URL="https://matomo.infinito.example"

# Deploy web-app-dashboard with matomo disabled to verify that SERVICES_DISABLED
# correctly suppresses a shared service in the generated inventory.
# web-app-dashboard is chosen as the host app because it is lightweight and
# has few dependencies, making it fast to deploy in CI.
SERVICES_DISABLED="matomo" make deploy-fresh-purged-app APPS="web-app-dashboard"

# Trust the local CA certificate so HTTPS endpoints are reachable from the host.
make trust-ca

# Verify the dashboard is reachable (matomo was disabled, not the dashboard itself).
assert_http_status 200 "${DASHBOARD_URL}"

# Verify matomo is not reachable because it was excluded from the inventory.
# The nginx proxy returns 404 when no upstream is configured for this host.
assert_http_status 404 "${MATOMO_URL}"

# Deploy web-app-matomo on top of the existing inventory so matomo becomes reachable.
# web-app-matomo is chosen because it has few dependencies and deploys quickly,
# making it ideal for environment validation without excessive resource usage.
make deploy-fresh-purged-app APPS="web-app-matomo"

# Verify matomo is now reachable after its dedicated deploy.
assert_http_status 200 "${MATOMO_URL}"

# Stop the compose stack and remove all volumes for a clean teardown.
make down

# Reverse the environment bootstrap (DNS, AppArmor, IPv6 settings).
make environment-teardown
