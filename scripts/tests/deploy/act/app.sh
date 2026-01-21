#!/usr/bin/env bash
set -euo pipefail

# Run local deploy workflow via act for a single app (linear matrix)
# Required:
#   APP              e.g. web-app-nextcloud
#   TEST_DEPLOY_TYPE server|workstation|universal
#   INFINITO_DISTRO  e.g. arch, debian, ubuntu

: "${APP:?APP is not set (e.g. APP=web-app-nextcloud)}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE is not set (server|workstation|universal)}"
: "${INFINITO_DISTRO:?INFINITO_DISTRO is not set (e.g. arch, debian, ubuntu)}"

case "${TEST_DEPLOY_TYPE}" in
  server|workstation|universal) ;;
  *)
    echo "Invalid TEST_DEPLOY_TYPE: ${TEST_DEPLOY_TYPE}" >&2
    echo "Allowed: server | workstation | universal" >&2
    exit 2
    ;;
esac

echo "=== act: deploy local (type=${TEST_DEPLOY_TYPE}, app=${APP}, distros=${INFINITO_DISTRO}) ==="

act workflow_dispatch \
  -W .github/workflows/test-deploy-local.yml \
  --env TEST_DEPLOY_TYPE="${TEST_DEPLOY_TYPE}" \
  --env DISTROS="${INFINITO_DISTRO}" \
  --env ONLY_APP="${APP}" \
  --container-options "--privileged" \
  --network host
