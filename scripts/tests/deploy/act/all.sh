#!/usr/bin/env bash
set -euo pipefail

# Run full local deploy workflow via act
# Expects:
#   TEST_DEPLOY_TYPE (optional) server|workstation|universal (default: server)
#   INFINITO_DISTRO  (optional) e.g. arch (default: arch)

TEST_DEPLOY_TYPE="${TEST_DEPLOY_TYPE:-server}"
INFINITO_DISTRO="${INFINITO_DISTRO:-arch}"

echo "=== act: deploy local (type=${TEST_DEPLOY_TYPE}, distros=${INFINITO_DISTRO}) ==="

act workflow_dispatch \
  -W .github/workflows/test-deploy-local.yml \
  --env TEST_DEPLOY_TYPE="${TEST_DEPLOY_TYPE}" \
  --env DISTROS="${INFINITO_DISTRO}" \
  --env ONLY_APP="" \
  --container-options "--privileged" \
  --network host
