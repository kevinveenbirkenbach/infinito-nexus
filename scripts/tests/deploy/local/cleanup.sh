#!/usr/bin/env bash
set -euo pipefail

# Cleanup a single app entity in the running infinito container.
# Expects:
#   APP               (required)  e.g. web-app-nextcloud
#   INFINITO_CONTAINER(required)  e.g. infinito_nexus_arch

: "${APP:?APP is not set (e.g. APP=web-app-nextcloud)}"
: "${INFINITO_CONTAINER:?INFINITO_CONTAINER is not set (e.g. infinito_nexus_arch)}"

echo "=== local cleanup: app=${APP} container=${INFINITO_CONTAINER} ==="

docker exec -it "${INFINITO_CONTAINER}" bash -lc "
  set -euo pipefail
  cd /opt/src/infinito

  entity=\"\$(python3 -c 'from module_utils.entity_name_utils import get_entity_name; print(get_entity_name(\"${APP}\"))')\"

  if [[ -z \"\${entity}\" ]]; then
    echo \"!!! WARNING: could not derive entity from APP=${APP} — skipping purge\"
    exit 0
  fi

  if [[ ! -d \"/opt/docker/\${entity}\" ]]; then
    echo \"!!! WARNING: /opt/docker/\${entity} not found — skipping purge\"
    exit 0
  fi

  echo \">>> Derived entity from APP=${APP}: \${entity}\"
  bash /opt/src/infinito/scripts/administration/purge_entity.sh \"\${entity}\" || true
"
