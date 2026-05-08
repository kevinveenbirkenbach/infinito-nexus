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

docker exec -e APPS="${APPS}" "${INFINITO_CONTAINER}" \
	bash /opt/src/infinito/scripts/container/purge/apps.sh
