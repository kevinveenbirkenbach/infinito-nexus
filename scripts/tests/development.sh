#!/usr/bin/env bash
set -euo pipefail

APPS="${APPS:-web-app-matomo}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# pkgmgr images may reset the working directory before invoking this script.
cd "${REPO_ROOT}"
bash "${REPO_ROOT}/scripts/install/package.sh"

make install
make environment-bootstrap
make up
make test
make deploy-fresh-purged-app APPS="${APPS}"
make trust-ca

MATOMO_URL="https://matomo.infinito.example"

echo "Checking matomo URL: ${MATOMO_URL}"
curl -sS -o /dev/null -w '%{http_code}\n' "${MATOMO_URL}" | grep -qx '200'

make down
make environment-teardown
