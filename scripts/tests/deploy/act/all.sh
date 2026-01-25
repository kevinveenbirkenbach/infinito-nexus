#!/usr/bin/env bash
set -euo pipefail

# Run full local deploy workflow via act (linear matrix)
# Required:
#   TEST_DEPLOY_TYPE  server|workstation|universal
#   INFINITO_DISTRO   e.g. arch, debian, ubuntu, fedora, centos

: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE must be set (server|workstation|universal)}"
: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set (e.g. arch, debian, ubuntu)}"

case "${TEST_DEPLOY_TYPE}" in
  server|workstation|universal) ;;
  *)
    echo "Invalid TEST_DEPLOY_TYPE: ${TEST_DEPLOY_TYPE}" >&2
    echo "Allowed: server | workstation | universal" >&2
    exit 2
    ;;
esac

echo "=== act: deploy local (type=${TEST_DEPLOY_TYPE}, distros=${INFINITO_DISTRO}) ==="

act workflow_dispatch \
  -W .github/workflows/test-deploy-local.yml \
  --env TEST_DEPLOY_TYPE="${TEST_DEPLOY_TYPE}" \
  --env DISTROS="${INFINITO_DISTRO}" \
  --env ONLY_APP="" \
  --container-options "--privileged" \
  --network host
