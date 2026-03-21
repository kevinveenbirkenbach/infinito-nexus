#!/usr/bin/env bash
set -euo pipefail

APP="${APP:-web-app-matomo}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

make install
make dev-environment-bootstrap
make up
make test-local-app APP="${APP}"
make trust-ca

MATOMO_URL="https://matomo.infinito.example"

echo "Checking matomo URL: ${MATOMO_URL}"
curl -sS -o /dev/null -w '%{http_code}\n' "${MATOMO_URL}" | grep -qx '200'

make down
make dev-environment-teardown
