#!/usr/bin/env bash
set -euo pipefail

# Run deploy for ALL apps using the already initialized local inventory.
#
# Required:
#   INFINITO_DISTRO   (arch|debian|ubuntu|fedora|centos)
#   TEST_DEPLOY_TYPE  (server|workstation|universal)
#
# Optional:
#   INVENTORY_BASE_DIR (default: /etc/inventories)
#   LIMIT_HOST         (default: localhost)
#   DEBUG              (default: false)
#   INCLUDE_RE / EXCLUDE_RE / FINAL_EXCLUDE_RE (to re-derive the same list)
#
# Notes:
# - This does NOT create the inventory. Run inventory-init-all.sh first.
# - We recompute the app list to keep behavior deterministic with filters.

: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set (arch|debian|ubuntu|fedora|centos)}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE must be set (server|workstation|universal)}"

INVENTORY_BASE_DIR="${INVENTORY_BASE_DIR:-/etc/inventories}"
LIMIT_HOST="${LIMIT_HOST:-localhost}"
DEBUG="${DEBUG:-false}"

normalize_bool() {
  case "${1:-}" in
    true|True|TRUE|1) echo "true" ;;
    false|False|FALSE|0|"") echo "false" ;;
    *) echo "ERROR: invalid boolean: ${1}" >&2; exit 2 ;;
  esac
}

DEBUG="$(normalize_bool "${DEBUG}")"

inv_dir="${INVENTORY_BASE_DIR}/local-full-${TEST_DEPLOY_TYPE}"
inv_file="${inv_dir}/servers.yml"
pw_file="${inv_dir}/.password"

if [[ ! -f "${inv_file}" ]]; then
  echo "ERROR: inventory not found: ${inv_file}" >&2
  echo "Run: make test-local-inventory-init-all" >&2
  exit 2
fi

if [[ ! -f "${pw_file}" ]]; then
  echo "ERROR: password file not found: ${pw_file}" >&2
  exit 2
fi

echo "=== local run (ALL apps) ==="
echo "distro   = ${INFINITO_DISTRO}"
echo "type     = ${TEST_DEPLOY_TYPE}"
echo "limit    = ${LIMIT_HOST}"
echo "debug    = ${DEBUG}"
echo "inv_file = ${inv_file}"
echo

# Ensure stack is up
python3 -m cli.deploy.development up \
  --distro "${INFINITO_DISTRO}" \
  --when-down \
  --skip-entry-init

# Recompute apps list (optional, but keeps filters consistent)
apps_json="$(
  TEST_DEPLOY_TYPE="${TEST_DEPLOY_TYPE}" \
  INCLUDE_RE="${INCLUDE_RE:-}" \
  EXCLUDE_RE="${EXCLUDE_RE:-}" \
  FINAL_EXCLUDE_RE="${FINAL_EXCLUDE_RE:-}" \
  scripts/meta/build-test-matrix.sh
)"

apps_count="$(
  python3 -c 'import json,sys; a=json.loads(sys.argv[1]); assert isinstance(a,list); print(len(a))' \
    "${apps_json}"
)"
if [[ "${apps_count}" == "0" ]]; then
  echo "ERROR: discovered apps list has length 0" >&2
  exit 2
fi

apps_csv="$(
  python3 -c 'import json,sys; a=json.loads(sys.argv[1]); print(",".join(map(str,a)))' \
    "${apps_json}"
)"

echo "apps_count=${apps_count}"
echo "apps_sample=$(
  python3 -c 'import json,sys; a=json.loads(sys.argv[1]); print(",".join(a[:8]) + ("..." if len(a)>8 else ""))' \
    "${apps_json}"
)"
echo

# Run deploy inside container
python3 -m cli.deploy.development exec \
  --distro "${INFINITO_DISTRO}" -- \
  bash -lc "
    set -euo pipefail
    cd /opt/src/infinito

    echo '>>> entry.sh bootstrap'
    ./scripts/docker/entry.sh true

    cmd=(infinito deploy dedicated '${inv_file}'
      -T '${TEST_DEPLOY_TYPE}'
      --skip-update
      --skip-backup
      --skip-cleanup
      --no-signal
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
