#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Required environment
# ---------------------------------------------------------------------------
: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set (arch|debian|ubuntu|fedora|centos)}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE must be set (server|workstation|universal)}"
: "${INVENTORY_DIR:?INVENTORY_DIR must be set (e.g. /etc/inventories/local-full-server)}"

# Optional overrides
LIMIT_HOST="${LIMIT_HOST:-localhost}"
WHITELIST="${WHITELIST:-}"

# This script always generates inventories for the development compose stack.
RUNTIME_VARS_JSON='{"RUNTIME":"dev"}'

echo "=== local full deploy (development compose stack) ==="
echo "distro        = ${INFINITO_DISTRO}"
echo "type          = ${TEST_DEPLOY_TYPE}"
echo "limit         = ${LIMIT_HOST}"
echo "inventory_dir = ${INVENTORY_DIR}"
echo "whitelist     = ${WHITELIST}"
echo

# ---------------------------------------------------------------------------
# 1) Bring up development stack (no build) on host
# ---------------------------------------------------------------------------
echo ">>> Starting development compose stack (no build)"
"${PYTHON}" -m cli.deploy.development up \
  --distro "${INFINITO_DISTRO}" \
  --skip-entry-init

# ---------------------------------------------------------------------------
# 2) Discover apps on HOST (needs docker compose)
# ---------------------------------------------------------------------------
echo ">>> Discovering apps on host via scripts/meta/resolve/apps.sh (TEST_DEPLOY_TYPE=${TEST_DEPLOY_TYPE})"

# IMPORTANT:
# - compose can emit warnings on STDOUT (depending on version/config)
# - we must guarantee JSON-only output for downstream parsing
# - PYTHON from host venv must NOT be used inside container exec calls
discover_out="$(
  set +e
  TEST_DEPLOY_TYPE="${TEST_DEPLOY_TYPE}" \
  WHITELIST="${WHITELIST}" \
  PYTHON=python3 \
  scripts/meta/resolve/apps.sh 2> >(cat >&2) \
  | jq -c 'if type=="array" then . else [] end' 2>/dev/null
  echo "rc=$?" >&2
)"
# Now discover_out should be compact JSON array or empty.

if [[ -z "${discover_out}" ]]; then
  echo "ERROR: apps discovery produced empty output" >&2
  echo "DEBUG: raw apps.sh output (first 50 lines):" >&2
  TEST_DEPLOY_TYPE="${TEST_DEPLOY_TYPE}" WHITELIST="${WHITELIST}" PYTHON=python3 \
    scripts/meta/resolve/apps.sh 2>&1 | sed -n '1,50p' >&2
  exit 2
fi

apps_json="${discover_out}"
echo "apps_json=${apps_json}"

# Validate JSON list + compute count
apps_count="$(
  "${PYTHON}" -c 'import json,sys; a=json.loads(sys.argv[1]); assert isinstance(a,list); print(len(a))' \
    "${apps_json}"
)"

if [[ "${apps_count}" == "0" ]]; then
  echo "ERROR: discovered apps list has length 0"
  exit 2
fi

# Convert JSON list -> CSV
apps_csv="$(
  "${PYTHON}" -c 'import json,sys; a=json.loads(sys.argv[1]); print(",".join(map(str,a)))' \
    "${apps_json}"
)"

if [[ -z "${apps_csv}" ]]; then
  echo "ERROR: apps_csv ended up empty even though apps_count=${apps_count}"
  echo "----- apps_json -----"
  printf '%s\n' "${apps_json}"
  echo "---------------------"
  exit 2
fi

echo "apps_count=${apps_count}"
echo

# ---------------------------------------------------------------------------
# 3) entry.sh + create inventory + deploy INSIDE container via development exec
# ---------------------------------------------------------------------------
echo ">>> Running entry/init + inventory + deploy inside infinito container via development exec"

"${PYTHON}" -m cli.deploy.development exec \
  --distro "${INFINITO_DISTRO}" -- \
  bash -c "
    set -euo pipefail
    cd /opt/src/infinito

    echo '>>> Running entry.sh bootstrap'
    ./scripts/docker/entry.sh true

    inv_dir='${INVENTORY_DIR}'
    inv_file=\"\${inv_dir}/${TEST_DEPLOY_TYPE}.yml\"
    pw_file=\"\${inv_dir}/.password\"

    mkdir -p \"\${inv_dir}\"

    if [[ ! -f \"\${pw_file}\" ]]; then
      printf '%s\n' 'local-vault-password' > \"\${pw_file}\"
      chmod 600 \"\${pw_file}\" || true
    fi

    echo \">>> Creating inventory at \${inv_file}\"
    echo \">>> Include apps (${apps_count}): ${apps_csv}\"

    infinito create inventory \"\${inv_dir}\" \
      --inventory-file \${inv_file} \
      --host '${LIMIT_HOST}' \
      --ssl-disabled \
      --vars '${RUNTIME_VARS_JSON}' \
      --vars-file inventories/dev.yml \
      --include '${apps_csv}'

    echo \">>> Deploying against \${inv_file}\"

    infinito deploy dedicated \"\${inv_file}\" \
      --skip-backup \
      --debug \
      --log /opt/src/infinito/logs \
      -l '${LIMIT_HOST}' \
      --diff \
      -vv \
      --password-file \"\${pw_file}\"
  "

echo
echo "=== local full deploy finished ==="
