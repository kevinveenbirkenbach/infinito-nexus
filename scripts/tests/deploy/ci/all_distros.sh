#!/usr/bin/env bash
set -euo pipefail

# SPOT: Deploy exactly ONE app across ALL distros (serial).
#
# Required env:
#   APP="web-app-keycloak"
#   TEST_DEPLOY_TYPE="server|workstation|universal"
#   DISTROS="arch debian ubuntu fedora centos"
#   INVENTORY_DIR="/path/to/inventory"
#
# Optional env:
#   PYTHON="python3"

: "${APP:?APP is required (e.g. APP=web-app-keycloak)}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE is required (server|workstation|universal)}"
: "${DISTROS:?DISTROS is required (e.g. 'arch debian ubuntu fedora centos')}"
: "${INVENTORY_DIR:?INVENTORY_DIR is required}"
export INVENTORY_DIR

PYTHON="${PYTHON:-python3}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
cd "${REPO_ROOT}"

read -r -a distro_arr <<< "${DISTROS}"

for distro in "${distro_arr[@]}"; do
  echo "=== Running dedicated distro deploy: distro=${distro} app=${APP} type=${TEST_DEPLOY_TYPE} ==="

  export INFINITO_DISTRO="${distro}"
  
  set +e
  scripts/tests/deploy/ci/dedicated_distro.sh \
    --type "${TEST_DEPLOY_TYPE}" \
    --app "${APP}"
  rc=$?
  set -e

  if [[ $rc -ne 0 ]]; then
    echo "[ERROR] Deploy failed for distro=${distro} app=${APP} (rc=${rc})" >&2
    exit "$rc"
  fi
done
