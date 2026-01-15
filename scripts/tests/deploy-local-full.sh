#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Required environment
# ---------------------------------------------------------------------------
: "${INFINITO_CONTAINER:?INFINITO_CONTAINER must be set (e.g. infinito_nexus_arch)}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE must be set (server|workstation|universal)}"

# Optional overrides
INVENTORY_BASE_DIR="${INVENTORY_BASE_DIR:-/etc/inventories}"
LIMIT_HOST="${LIMIT_HOST:-localhost}"

echo "=== local full deploy ==="
echo "container = ${INFINITO_CONTAINER}"
echo "type      = ${TEST_DEPLOY_TYPE}"
echo "limit     = ${LIMIT_HOST}"
echo

# ---------------------------------------------------------------------------
# 1) Discover apps on HOST (needs docker compose)
# ---------------------------------------------------------------------------
echo ">>> Discovering apps on host via make ci-deploy-discover (TEST_DEPLOY_TYPE=${TEST_DEPLOY_TYPE})"

discover_out="$(
  TEST_DEPLOY_TYPE="${TEST_DEPLOY_TYPE}" \
  make -s --no-print-directory ci-deploy-discover
)"

if [[ -z "${discover_out}" ]]; then
  echo "ERROR: ci-deploy-discover returned empty output"
  exit 2
fi

apps_json="${discover_out}"
echo "apps_json=${apps_json}"

# Validate JSON list + compute count
apps_count="$(
  python3 -c 'import json,sys; a=json.loads(sys.argv[1]); assert isinstance(a,list); print(len(a))' \
    "${apps_json}"
)"

if [[ "${apps_count}" == "0" ]]; then
  echo "ERROR: discovered apps list has length 0"
  exit 2
fi

# Convert JSON list -> CSV
apps_csv="$(
  python3 -c 'import json,sys; a=json.loads(sys.argv[1]); print(",".join(map(str,a)))' \
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
# 2) Run entry.sh + create inventory + deploy INSIDE container
# ---------------------------------------------------------------------------
docker exec -t "${INFINITO_CONTAINER}" bash -lc "
  set -euo pipefail
  cd /opt/src/infinito

  echo '>>> Running entry.sh bootstrap'
  ./scripts/docker/entry.sh true

  inv_dir='${INVENTORY_BASE_DIR}/local-full-${TEST_DEPLOY_TYPE}'
  inv_file=\"\${inv_dir}/servers.yml\"
  pw_file=\"\${inv_dir}/.password\"

  mkdir -p \"\${inv_dir}\"

  if [[ ! -f \"\${pw_file}\" ]]; then
    printf '%s\n' 'local-vault-password' > \"\${pw_file}\"
    chmod 600 \"\${pw_file}\" || true
  fi

  echo '>>> Creating inventory at' \"\${inv_file}\"
  echo '>>> Include apps count: ${apps_count}'
  # Avoid printing the full CSV (it is huge); show first few instead:
  echo '>>> Include sample:' \"\$(python3 - <<'PY'
import sys
csv=sys.argv[1]
items=csv.split(',')
print(','.join(items[:8]) + ('...' if len(items)>8 else ''))
PY
'${apps_csv}')\"

  python3 -m cli.create.inventory \"\${inv_dir}\" \
    --host ${LIMIT_HOST} \
    --ssl-disabled \
    --vars-file inventory.sample.yml \
    --include '${apps_csv}'

  echo '>>> Deploying against' \"\${inv_file}\"

  infinito deploy dedicated \"\${inv_file}\" \
    -T '${TEST_DEPLOY_TYPE}' \
    --skip-update \
    --skip-backup \
    -l ${LIMIT_HOST} \
    --diff \
    -vv \
    --password-file \"\${pw_file}\"
"

echo
echo "=== local full deploy finished ==="
