#!/usr/bin/env bash
set -euo pipefail

APP="${APP:-web-app-dashboard}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# pkgmgr images may reset the working directory before invoking this script.
cd "${REPO_ROOT}"
bash "${REPO_ROOT}/scripts/install/package.sh"

make install
make dev-environment-bootstrap
make up
make test
make test-local-dedicated APP="${APP}"
make trust-ca

DASHBOARD_URL="https://dashboard.infinito.example"

echo "Checking dashboard URL: ${DASHBOARD_URL}"
curl -sS -o /dev/null -w '%{http_code}\n' "${DASHBOARD_URL}" | grep -qx '200'

make down
make dev-environment-teardown
