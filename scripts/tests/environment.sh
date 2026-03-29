#!/usr/bin/env bash
set -euo pipefail

# web-app-matomo is chosen because it has few dependencies and deploys quickly,
# making it ideal for environment validation without excessive resource usage.
APPS="web-app-matomo"
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

# Create a fresh inventory, purge prior app state, and deploy the target app(s).
make deploy-fresh-purged-app APPS="${APPS}"

# Trust the local CA certificate so HTTPS endpoints are reachable from the host.
make trust-ca

MATOMO_URL="https://matomo.infinito.example"

# Verify the deployed app responds with HTTP 200.
echo "Checking matomo URL: ${MATOMO_URL}"
curl -sS -o /dev/null -w '%{http_code}\n' "${MATOMO_URL}" | grep -qx '200'

# Stop the compose stack and remove all volumes for a clean teardown.
make down

# Reverse the environment bootstrap (DNS, AppArmor, IPv6 settings).
make environment-teardown
