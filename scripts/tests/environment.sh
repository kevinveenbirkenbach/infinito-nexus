#!/usr/bin/env bash
set -euo pipefail

APP="${APP:-web-app-dashboard}"

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
make down
make dev-environment-teardown
