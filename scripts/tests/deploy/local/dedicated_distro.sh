#!/usr/bin/env bash
set -euo pipefail

# Local: Deploy exactly ONE app on ONE distro, twice, against the same stack.
# Same logic as CI version, but WITHOUT destructive cleanup.
#
# Required env:
#   INFINITO_DISTRO     arch|debian|ubuntu|fedora|centos
#   INVENTORY_DIR       /etc/inventories/local-full-server
#   TEST_DEPLOY_TYPE    server|workstation|universal
#   APP                 web-app-*
#
# Optional:
#   PYTHON=python3
#   LIMIT_HOST=localhost

PYTHON="${PYTHON:-python3}"

: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set (e.g. arch)}"
: "${INVENTORY_DIR:?INVENTORY_DIR must be set}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE must be set (server|workstation|universal)}"
: "${APP:?APP must be set (e.g. web-app-keycloak)}"

LIMIT_HOST="${LIMIT_HOST:-localhost}"

case "${TEST_DEPLOY_TYPE}" in
  server|workstation|universal) ;;
  *)
    echo "[ERROR] Invalid TEST_DEPLOY_TYPE: ${TEST_DEPLOY_TYPE}" >&2
    exit 2
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
cd "${REPO_ROOT}"

echo "=== LOCAL: distro=${INFINITO_DISTRO} type=${TEST_DEPLOY_TYPE} app=${APP} (debug always on) ==="
echo "limit_host=${LIMIT_HOST}"
echo "inventory_dir=${INVENTORY_DIR}"
echo

echo ">>> Ensuring stack is up for distro ${INFINITO_DISTRO}"
"${PYTHON}" -m cli.deploy.development up \
  --distro "${INFINITO_DISTRO}" \
  --when-down

echo ">>> Running everything inside container via development exec (no logic changes)"
"${PYTHON}" -m cli.deploy.development exec \
  --distro "${INFINITO_DISTRO}" -- \
  bash -lc "
    set -euo pipefail
    cd /opt/src/infinito

    echo '>>> Running entry.sh'
    ./scripts/docker/entry.sh true

    echo '>>> Pre-cleanup shared entities'
    APP='matomo' \
    INFINITO_CONTAINER=\"\${INFINITO_CONTAINER:-}\" \
    scripts/tests/deploy/local/utils/purge/entity.sh

    deploy_args=(
      --distro '${INFINITO_DISTRO}'
      --type '${TEST_DEPLOY_TYPE}'
      --app '${APP}'
      --inventory-dir '${INVENTORY_DIR}'
      --debug
    )

    echo '>>> PASS 1: init inventory (ASYNC_ENABLED=false)'
    ${PYTHON} -m cli.deploy.development init \
      --distro '${INFINITO_DISTRO}' \
      --app '${APP}' \
      --inventory-dir '${INVENTORY_DIR}' \
      --vars '{\"ASYNC_ENABLED\": false}'

    echo '>>> PASS 1: deploy'
    ${PYTHON} -m cli.deploy.development deploy \"\${deploy_args[@]}\"

    echo '>>> PASS 2: re-init inventory (ASYNC_ENABLED=true)'
    ${PYTHON} -m cli.deploy.development init \
      --distro '${INFINITO_DISTRO}' \
      --app '${APP}' \
      --inventory-dir '${INVENTORY_DIR}' \
      --vars '{\"ASYNC_ENABLED\": true}'

    echo '>>> PASS 2: deploy'
    ${PYTHON} -m cli.deploy.development deploy \"\${deploy_args[@]}\"
  "

echo
echo "✅ Done (no deletion)."
