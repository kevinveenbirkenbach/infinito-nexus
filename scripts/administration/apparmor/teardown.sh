#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/administration/apparmor/common.sh
source "${SCRIPT_DIR}/common.sh"

echo "[apparmor] tearing down (dev mode)"

if ! apparmor_should_manage; then
	echo "[apparmor] skipping teardown: $(apparmor_skip_reason)"
	exit 0
fi

if apparmor_service_exists; then
	systemctl stop apparmor || true
else
	echo "[apparmor] apparmor.service not available or systemd inactive; skipping service stop"
fi

if command -v aa-teardown >/dev/null 2>&1; then
	aa-teardown || apparmor_warn "[apparmor] aa-teardown returned non-zero; continuing"
elif command -v apparmor_parser >/dev/null 2>&1 && compgen -G '/etc/apparmor.d/*' >/dev/null; then
	apparmor_parser -R /etc/apparmor.d/* || true
else
	echo "[apparmor] no AppArmor profile tooling available; skipping profile unload"
fi

echo "[apparmor] teardown complete"
