#!/usr/bin/env bash
set -euo pipefail

# Run local deploy workflow via act for a single app (linear matrix)
# Required:
#   APPS             e.g. web-app-nextcloud
#   TEST_DEPLOY_TYPE server|workstation|universal
#   INFINITO_DISTRO  e.g. arch, debian, ubuntu

: "${APPS:?APPS is not set (e.g. APPS=web-app-nextcloud)}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE is not set (server|workstation|universal)}"
: "${INFINITO_DISTRO:?INFINITO_DISTRO is not set (e.g. arch, debian, ubuntu)}"

case "${TEST_DEPLOY_TYPE}" in
server | workstation | universal) ;;
*)
	echo "Invalid TEST_DEPLOY_TYPE: ${TEST_DEPLOY_TYPE}" >&2
	echo "Allowed: server | workstation | universal" >&2
	exit 2
	;;
esac

echo "=== act: deploy local (type=${TEST_DEPLOY_TYPE}, app=${APPS}, distros=${INFINITO_DISTRO}) ==="

act workflow_dispatch \
	-W .github/workflows/test-deploy-local.yml \
	--input test_deploy_type="${TEST_DEPLOY_TYPE}" \
	--input distros="${INFINITO_DISTRO}" \
	--input whitelist="${APPS}" \
	--container-options "--privileged" \
	--network host
