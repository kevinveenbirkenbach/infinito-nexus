#!/usr/bin/env bash
set -euo pipefail

# Fresh-purged deploy: run exactly ONE app on ONE distro against the same stack.
# Same logic as CI version, but WITHOUT destructive cleanup.
#
# Required env:
#   INFINITO_DISTRO     arch|debian|ubuntu|fedora|centos
#   INVENTORY_DIR       /etc/inventories/local-full-server
#   TEST_DEPLOY_TYPE    server|workstation|universal
#   APPS                web-app-*
#
# Optional:
#   FULL_CYCLE=false    Default. Deploy only (pass 1). Set to 'true' to also run the update pass (pass 2).
#   PYTHON=python3
#   LIMIT_HOST=localhost

PYTHON="${PYTHON:-python3}"
FULL_CYCLE="${FULL_CYCLE:-false}"

: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set (e.g. arch)}"
: "${INVENTORY_DIR:?INVENTORY_DIR must be set}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE must be set (server|workstation|universal)}"
: "${APPS:?APPS must be set (e.g. web-app-keycloak)}"

LIMIT_HOST="${LIMIT_HOST:-localhost}"

case "${TEST_DEPLOY_TYPE}" in
server | workstation | universal) ;;
*)
	echo "[ERROR] Invalid TEST_DEPLOY_TYPE: ${TEST_DEPLOY_TYPE}" >&2
	exit 2
	;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"
cd "${REPO_ROOT}"

echo "=== LOCAL: distro=${INFINITO_DISTRO} type=${TEST_DEPLOY_TYPE} app=${APPS} full_cycle=${FULL_CYCLE} ==="
echo "limit_host=${LIMIT_HOST}"
echo "inventory_dir=${INVENTORY_DIR}"
echo

echo ">>> Ensuring stack is up for distro ${INFINITO_DISTRO}"
"${PYTHON}" -m cli.deploy.development up \
	--distro "${INFINITO_DISTRO}" \
	--when-down

echo ">>> Pre-cleanup shared entities (host docker context)"
target_container="infinito_nexus_${INFINITO_DISTRO}"
APPS='matomo' \
	INFINITO_CONTAINER="${INFINITO_CONTAINER:-${target_container}}" \
	scripts/tests/deploy/local/purge/entity.sh

echo ">>> Running entry.sh inside container"
"${PYTHON}" -m cli.deploy.development exec \
	--distro "${INFINITO_DISTRO}" -- \
	bash -lc "
    set -euo pipefail
    cd /opt/src/infinito

    echo '>>> Running entry.sh'
    ./scripts/docker/entry.sh true
  "

deploy_args=(
	--distro "${INFINITO_DISTRO}"
	--apps "${APPS}"
	--inventory-dir "${INVENTORY_DIR}"
	--debug
)

run_pass() {
	local label="$1"
	local async_enabled="$2"

	echo ">>> ${label}: init inventory (ASYNC_ENABLED=${async_enabled})"
	"${PYTHON}" -m cli.deploy.development init \
		--distro "${INFINITO_DISTRO}" \
		--apps "${APPS}" \
		--inventory-dir "${INVENTORY_DIR}" \
		--vars "{\"ASYNC_ENABLED\": ${async_enabled}}"

	echo ">>> ${label}: deploy"
	"${PYTHON}" -m cli.deploy.development deploy "${deploy_args[@]}"
}

run_pass "PASS 1" "false"

if [[ "${FULL_CYCLE}" == "true" ]]; then
	run_pass "PASS 2" "true"
else
	echo ">>> PASS 2 skipped (FULL_CYCLE=false)"
fi

echo
echo "✅ Done (no deletion)."
