#!/usr/bin/env bash
set -euo pipefail

# Cleanup one or multiple app entities in the running infinito container.
#
# Expects:
#   APPS               (required)
#     Examples:
#       APPS=web-app-nextcloud
#       APPS="web-app-nextcloud web-app-keycloak"
#       APPS="web-app-nextcloud,web-app-keycloak"
#
#   INFINITO_CONTAINER (required)
#     Example:
#       infinito_nexus_arch

: "${APPS:?APPS is not set (e.g. APPS=web-app-nextcloud)}"
: "${INFINITO_CONTAINER:?INFINITO_CONTAINER is not set (e.g. infinito_nexus_arch)}"

echo "=== local cleanup: APPS=${APPS} container=${INFINITO_CONTAINER} ==="

docker exec "${INFINITO_CONTAINER}" bash -lc "
  set -euo pipefail
  cd /opt/src/infinito

  # Normalize APPS list: commas -> spaces, then split on whitespace
  apps_raw=\"${APPS}\"
  apps_raw=\"\${apps_raw//,/ }\"
  read -r -a apps <<< \"\${apps_raw}\"

  if [[ \"\${#apps[@]}\" -lt 1 ]]; then
    echo \"!!! WARNING: APPS is empty after parsing — skipping purge\"
    exit 0
  fi

  declare -A seen_entities=()
  entities=()

  # Reuse central Python env resolution instead of custom detection.
  if [[ -f \"scripts/meta/env/python.sh\" ]]; then
    # shellcheck source=scripts/meta/env/python.sh
    source \"scripts/meta/env/python.sh\"
  fi
  python_bin=\"\${PYTHON:-python3}\"

  for app in \"\${apps[@]}\"; do
    [[ -n \"\${app}\" ]] || continue

    entity=\"\$(\"\${python_bin}\" -c 'from utils.entity_name_utils import get_entity_name; import sys; print(get_entity_name(sys.argv[1]) or \"\")' \"\${app}\")\"

    if [[ -z \"\${entity}\" ]]; then
      echo \"!!! WARNING: could not derive entity from APPS=\${app} — skipping\"
      continue
    fi

    if [[ ! -d \"/opt/compose/\${entity}\" ]]; then
      echo \"!!! WARNING: /opt/compose/\${entity} not found for APPS=\${app} — skipping\"
      continue
    fi

    if [[ -z \"\${seen_entities[\${entity}]:-}\" ]]; then
      seen_entities[\${entity}]=1
      entities+=(\"\${entity}\")
      echo \">>> Derived entity from APPS=\${app}: \${entity}\"
    fi
  done

  if [[ \"\${#entities[@]}\" -lt 1 ]]; then
    echo \"!!! WARNING: no valid entities found — nothing to purge\"
    exit 0
  fi

  echo \">>> Purging entities: \${entities[*]}\"
  bash /opt/src/infinito/scripts/container/purge/entity/all.sh \"\${entities[@]}\" || true
"
