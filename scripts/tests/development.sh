#!/usr/bin/env bash
set -euo pipefail

APP="${APP:-web-app-dashboard}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# pkgmgr images may reset the working directory before invoking this script.
cd "${REPO_ROOT}"

if command -v pacman >/dev/null 2>&1; then
	pacman -Sy --noconfirm --needed jq
elif command -v apt-get >/dev/null 2>&1; then
	export DEBIAN_FRONTEND=noninteractive
	apt-get update
	apt-get install -y --no-install-recommends jq
	rm -rf /var/lib/apt/lists/*
else
	echo "Unsupported package manager for jq installation" >&2
	exit 1
fi

make install
make dev-environment-bootstrap
make up
make test
make test-local-rapid APP="${APP}"
make trust-ca

DASHBOARD_URL="https://dashboard.infinito.example"

echo "Checking dashboard URL: ${DASHBOARD_URL}"
curl -sS -o /dev/null -w '%{http_code}\n' "${DASHBOARD_URL}" | grep -qx '200'

make down
make dev-environment-teardown
