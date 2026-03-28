#!/usr/bin/env bash
set -euo pipefail

# Rapid deploy for a single app inside the running infinito container.
# Expects (ALL required):
#   APP                e.g. web-app-nextcloud
#   TEST_DEPLOY_TYPE   server|workstation|universal
#   INFINITO_CONTAINER e.g. infinito_nexus_arch
#   DEBUG              true|false
#   INVENTORY_DIR      e.g. /etc/inventories/local-full-server

: "${APP:?APP is not set (e.g. APP=web-app-nextcloud)}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE is not set (server|workstation|universal)}"
: "${INFINITO_CONTAINER:?INFINITO_CONTAINER is not set (e.g. infinito_nexus_arch)}"
: "${DEBUG:?DEBUG is not set (true|false)}"
: "${INVENTORY_DIR:?INVENTORY_DIR is not set (e.g. INVENTORY_DIR=/etc/inventories/local-full-server)}"
inv_file="${INVENTORY_DIR}/devices.yml"
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

echo "=== rapid deploy: type=${TEST_DEPLOY_TYPE} app=${APP} container=${INFINITO_CONTAINER} debug=${DEBUG} ==="
echo "inventory_dir=${INVENTORY_DIR}"

docker exec "${INFINITO_CONTAINER}" bash -c "
  set -euo pipefail
  cd /opt/src/infinito

  if [[ ! -f \"${inv_file}\" ]]; then
    echo \"ERROR: inventory not found: ${inv_file}\" >&2
    exit 2
  fi

  if [[ ! -f \"${pw_file}\" ]]; then
    echo \"ERROR: password file not found: ${pw_file}\" >&2
    exit 2
  fi

  echo \">>> Running entry.sh\"
  ./scripts/docker/entry.sh true

  echo \">>> Starting rapid deploy\"
  cmd=(infinito deploy dedicated \"${inv_file}\"
    --skip-backup
    --skip-cleanup
    --id ${APP}
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
