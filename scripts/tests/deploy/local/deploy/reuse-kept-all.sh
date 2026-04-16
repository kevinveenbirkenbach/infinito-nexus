#!/usr/bin/env bash
set -euo pipefail

# Reuse-kept deploy for ALL apps using the already initialized local inventory.
#
# Required:
#   INFINITO_DISTRO   (arch|debian|ubuntu|fedora|centos)
#   TEST_DEPLOY_TYPE  (server|workstation|universal)
#   INVENTORY_DIR     (e.g. /etc/inventories/local-full-server)
#
# Optional:
#   LIMIT_HOST         (default: localhost)
#   DEBUG              (default: false)
#
# Notes:
# - This does NOT create the inventory. Run make deploy-fresh-kept-apps APPS=<role> first.
# - We recompute the app list to keep behavior deterministic with filters.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=scripts/tests/deploy/local/utils/lib.sh
source "${SCRIPT_DIR}/../utils/lib.sh"

REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"
cd "${REPO_ROOT}"

: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set (arch|debian|ubuntu|fedora|centos)}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE must be set (server|workstation|universal)}"
: "${INVENTORY_DIR:?INVENTORY_DIR must be set (e.g. /etc/inventories/local-full-server)}"

LIMIT_HOST="${LIMIT_HOST:-localhost}"

DEBUG="$(normalize_bool_or_default "${DEBUG:-}" false DEBUG)"

inv_dir="${INVENTORY_DIR}"
inv_file="${inv_dir}/devices.yml"
pw_file="${inv_dir}/.password"

if [[ ! -f "${inv_file}" ]]; then
	echo "ERROR: inventory not found: ${inv_file}" >&2
	echo "Run: make deploy-fresh-kept-apps APPS=<role>" >&2
	exit 2
fi

if [[ ! -f "${pw_file}" ]]; then
	echo "ERROR: password file not found: ${pw_file}" >&2
	exit 2
fi

echo "=== local run (ALL apps) ==="
echo "distro        = ${INFINITO_DISTRO}"
echo "type          = ${TEST_DEPLOY_TYPE}"
echo "limit         = ${LIMIT_HOST}"
echo "debug         = ${DEBUG}"
echo "inventory_dir = ${inv_dir}"
echo "inv_file      = ${inv_file}"
echo

# Ensure stack is up
"${PYTHON}" -m cli.deploy.development up \
	--distro "${INFINITO_DISTRO}" \
	--when-down \
	--skip-entry-init

# Recompute apps list (optional, but keeps filters consistent)
apps_json="$(
	TEST_DEPLOY_TYPE="${TEST_DEPLOY_TYPE}" \
		WHITELIST="${WHITELIST:-}" \
		scripts/meta/resolve/apps.sh
)"

apps_count="$(
	"${PYTHON}" -c 'import json,sys; a=json.loads(sys.argv[1]); assert isinstance(a,list); print(len(a))' \
		"${apps_json}"
)"
if [[ "${apps_count}" == "0" ]]; then
	echo "ERROR: discovered apps list has length 0" >&2
	exit 2
fi

echo "apps_count=${apps_count}"
echo "apps_sample=$(
	"${PYTHON}" -c 'import json,sys; a=json.loads(sys.argv[1]); print(",".join(a[:8]) + ("..." if len(a)>8 else ""))' \
		"${apps_json}"
)"
echo

# Run deploy inside container
"${PYTHON}" -m cli.deploy.development exec \
	--distro "${INFINITO_DISTRO}" -- \
	bash -c "
    set -euo pipefail
    cd /opt/src/infinito

    echo '>>> entry.sh bootstrap'
    ./scripts/docker/entry.sh true

    cmd=(infinito deploy dedicated '${inv_file}'
      --skip-backup
      --skip-cleanup
      -l '${LIMIT_HOST}'
      --diff
      -vv
      --password-file '${pw_file}'
      -e ASYNC_ENABLED=false
      -e SYS_SERVICE_ALL_ENABLED=false
      -e SYS_SERVICE_DEFAULT_STATE=started
    )

    if [[ '${DEBUG}' == 'true' ]]; then
      cmd+=(--debug)
    fi

    echo '>>> running:'
    printf ' %q' \"\${cmd[@]}\"
    echo

    exec \"\${cmd[@]}\"
  "

echo
echo "✅ Local run finished."
