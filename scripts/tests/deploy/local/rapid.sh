#!/usr/bin/env bash
set -euo pipefail

# Rapid deploy for a single app inside the running infinito container.
# Expects:
#   APP              (required) e.g. web-app-nextcloud
#   TEST_DEPLOY_TYPE (optional) server|workstation|universal (default: server)
#   INFINITO_CONTAINER (required)
#   DEBUG            (optional) "true"|"false" (default: true)

: "${APP:?APP is not set (e.g. APP=web-app-nextcloud)}"
: "${INFINITO_CONTAINER:?INFINITO_CONTAINER is not set (e.g. infinito_nexus_arch)}"

TEST_DEPLOY_TYPE="${TEST_DEPLOY_TYPE:-server}"
DEBUG="${DEBUG:-true}"

echo "=== rapid deploy: type=${TEST_DEPLOY_TYPE} app=${APP} container=${INFINITO_CONTAINER} debug=${DEBUG} ==="

docker exec -it "${INFINITO_CONTAINER}" bash -lc "
  set -euo pipefail
  cd /opt/src/infinito

  echo \">>> Running entry.sh\"
  ./scripts/docker/entry.sh true

  echo \">>> Starting rapid deploy\"
  cmd=(infinito deploy dedicated \"/etc/inventories/local-full-${TEST_DEPLOY_TYPE}/servers.yml\"
    -T \"${TEST_DEPLOY_TYPE}\"
    --skip-update
    --skip-backup
    --skip-cleanup
    --id \"${APP}\"
    --no-signal
    -l localhost
    --diff
    -vv
    --password-file \"/etc/inventories/local-full-${TEST_DEPLOY_TYPE}/.password\"
    -e ASYNC_ENABLED=false
    -e SYS_SERVICE_ALL_ENABLED=false
    -e SYS_SERVICE_DEFAULT_STATE=started
  )

  if [[ \"${DEBUG}\" == \"true\" ]]; then
    cmd+=(--debug)
  fi

  exec \"\${cmd[@]}\"
"
