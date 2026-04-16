#!/usr/bin/env bash
set -euo pipefail

# Reuse-kept deploy for a single app inside the running infinito container.
# Expects (ALL required):
#   APPS               e.g. web-app-nextcloud
#   TEST_DEPLOY_TYPE   server|workstation|universal
#   INFINITO_CONTAINER e.g. infinito_nexus_arch
#   DEBUG              true|false
#   INVENTORY_DIR      e.g. /etc/inventories/local-full-server

: "${APPS:?APPS is not set (e.g. APPS=web-app-nextcloud)}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE is not set (server|workstation|universal)}"
: "${INFINITO_CONTAINER:?INFINITO_CONTAINER is not set (e.g. infinito_nexus_arch)}"
: "${DEBUG:?DEBUG is not set (true|false)}"
: "${INVENTORY_DIR:?INVENTORY_DIR is not set (e.g. INVENTORY_DIR=/etc/inventories/local-full-server)}"
: "${INVENTORY_FILE:?INVENTORY_FILE is not set — source scripts/meta/env/inventory.sh first}"
pw_file="${INVENTORY_DIR}/.password"

case "${TEST_DEPLOY_TYPE}" in
server | workstation | universal) ;;
*)
	echo "Invalid TEST_DEPLOY_TYPE: ${TEST_DEPLOY_TYPE}" >&2
	echo "Allowed: server | workstation | universal" >&2
	exit 2
	;;
esac

case "${DEBUG}" in
true | false) ;;
*)
	echo "Invalid DEBUG: ${DEBUG}" >&2
	echo "Allowed: true | false" >&2
	exit 2
	;;
esac

echo "=== rapid deploy: type=${TEST_DEPLOY_TYPE} app=${APPS} container=${INFINITO_CONTAINER} debug=${DEBUG} ==="
echo "inventory_dir=${INVENTORY_DIR}"

docker exec \
	-e SERVICES_DISABLED="${SERVICES_DISABLED:-}" \
	"${INFINITO_CONTAINER}" bash -c "
  set -euo pipefail
  cd /opt/src/infinito

  if [[ ! -f \"${INVENTORY_FILE}\" ]]; then
    echo \"ERROR: inventory not found: ${INVENTORY_FILE}\" >&2
    exit 2
  fi

  if [[ ! -f \"${pw_file}\" ]]; then
    echo \"ERROR: password file not found: ${pw_file}\" >&2
    exit 2
  fi

  echo \">>> Running entry.sh\"
  ./scripts/docker/entry.sh true

  echo \">>> Starting rapid deploy\"
  cmd=(infinito deploy dedicated \"${INVENTORY_FILE}\"
    --skip-backup
    --skip-cleanup
    --id ${APPS}
    -l localhost
    --diff
    -vv
    --password-file \"${pw_file}\"
    -e ASYNC_ENABLED=false
    -e SYS_SERVICE_ALL_ENABLED=false
    -e SYS_SERVICE_DEFAULT_STATE=started
  )

  if [[ \"${DEBUG}\" == \"true\" ]]; then
    cmd+=(--debug)
  fi

  exec \"\${cmd[@]}\"
"
