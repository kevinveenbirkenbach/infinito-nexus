#!/usr/bin/env bash
set -euo pipefail

# Cleanup one or multiple app entities in the running infinito container.
#
# Expects:
#   APP                (required)
#     Examples:
#       APP=web-app-nextcloud
#       APP="web-app-nextcloud web-app-keycloak"
#       APP="web-app-nextcloud,web-app-keycloak"
#
#   INFINITO_CONTAINER (required)
#     Example:
#       infinito_nexus_arch

: "${APP:?APP is not set (e.g. APP=web-app-nextcloud)}"
: "${INFINITO_CONTAINER:?INFINITO_CONTAINER is not set (e.g. infinito_nexus_arch)}"

echo "=== local cleanup: APP=${APP} container=${INFINITO_CONTAINER} ==="

docker exec -it "${INFINITO_CONTAINER}" bash -lc "
  set -euo pipefail
  cd /opt/src/infinito

  # Normalize APP list: commas -> spaces, then split on whitespace
  apps_raw=\"${APP}\"
  apps_raw=\"\${apps_raw//,/ }\"
  read -r -a apps <<< \"\${apps_raw}\"

  if [[ \"\${#apps[@]}\" -lt 1 ]]; then
    echo \"!!! WARNING: APP is empty after parsing — skipping purge\"
    exit 0
  fi

  declare -A seen_entities=()
  entities=()

  for app in \"\${apps[@]}\"; do
    [[ -n \"\${app}\" ]] || continue

    entity=\"\$(python3 -c 'from module_utils.entity_name_utils import get_entity_name; import sys; print(get_entity_name(sys.argv[1]) or \"\")' \"\${app}\")\"

    if [[ -z \"\${entity}\" ]]; then
      echo \"!!! WARNING: could not derive entity from APP=\${app} — skipping\"
      continue
    fi

    if [[ ! -d \"/opt/compose/\${entity}\" ]]; then
      echo \"!!! WARNING: /opt/compose/\${entity} not found for APP=\${app} — skipping\"
      continue
    fi

    if [[ -z \"\${seen_entities[\${entity}]:-}\" ]]; then
      seen_entities[\${entity}]=1
      entities+=(\"\${entity}\")
      echo \">>> Derived entity from APP=\${app}: \${entity}\"
    fi
  done

  if [[ \"\${#entities[@]}\" -lt 1 ]]; then
    echo \"!!! WARNING: no valid entities found — nothing to purge\"
    exit 0
  fi

  echo \">>> Purging entities: \${entities[*]}\"
  bash /opt/src/infinito/scripts/administration/purge/entity/all.sh \"\${entities[@]}\" || true
"
