#!/usr/bin/env bash
set -euo pipefail

# Initialize a local inventory for ALL discovered apps.
#
# Required:
#   INFINITO_DISTRO   (arch|debian|ubuntu|fedora|centos)
#   TEST_DEPLOY_TYPE  (server|workstation|universal)
#   INVENTORY_DIR     (e.g. /etc/inventories/local-full-server)
#
# Optional:
#   INCLUDE_RE / EXCLUDE_RE / FINAL_EXCLUDE_RE (forwarded to build-test-matrix.sh)

: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set (arch|debian|ubuntu|fedora|centos)}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE must be set (server|workstation|universal)}"
: "${INVENTORY_DIR:?INVENTORY_DIR must be set (e.g. /etc/inventories/local-full-server)}"

# This script always generates inventories for the development compose stack.
RUNTIME_VARS_JSON='{"RUNTIME":"dev"}'

echo "=== local inventory init (ALL apps) ==="
echo "distro        = ${INFINITO_DISTRO}"
echo "type          = ${TEST_DEPLOY_TYPE}"
echo "inventory_dir = ${INVENTORY_DIR}"
echo

# 1) Discover apps on HOST (same as local/all.sh)
apps_json="$(
  TEST_DEPLOY_TYPE="${TEST_DEPLOY_TYPE}" \
  INCLUDE_RE="${INCLUDE_RE:-}" \
  EXCLUDE_RE="${EXCLUDE_RE:-}" \
  FINAL_EXCLUDE_RE="${FINAL_EXCLUDE_RE:-}" \
  scripts/meta/build-test-matrix.sh
)"

if [[ -z "${apps_json}" ]]; then
  echo "ERROR: build-test-matrix returned empty output" >&2
  exit 2
fi

apps_count="$(
  "${PYTHON}" -c 'import json,sys; a=json.loads(sys.argv[1]); assert isinstance(a,list); print(len(a))' \
    "${apps_json}"
)"

if [[ "${apps_count}" == "0" ]]; then
  echo "ERROR: discovered apps list has length 0" >&2
  echo "apps_json=${apps_json}" >&2
  exit 2
fi

apps_csv="$(
  "${PYTHON}" -c 'import json,sys; a=json.loads(sys.argv[1]); print(",".join(map(str,a)))' \
    "${apps_json}"
)"

if [[ -z "${apps_csv}" ]]; then
  echo "ERROR: apps_csv ended up empty even though apps_count=${apps_count}" >&2
  exit 2
fi

echo "apps_count=${apps_count}"
echo "apps_sample=$(
  "${PYTHON}" -c 'import json,sys; a=json.loads(sys.argv[1]); print(",".join(a[:8]) + ("..." if len(a)>8 else ""))' \
    "${apps_json}"
)"
echo

# 2) Bring up development stack (no build)
echo ">>> Starting development compose stack (no build)"
"${PYTHON}" -m cli.deploy.development up \
  --distro "${INFINITO_DISTRO}" \
  --skip-entry-init

# 3) Run entry.sh + create inventory INSIDE container
echo ">>> Initializing inventory inside container"

"${PYTHON}" -m cli.deploy.development exec \
  --distro "${INFINITO_DISTRO}" -- \
  bash -lc "
    set -euo pipefail
    cd /opt/src/infinito

    echo '>>> entry.sh bootstrap'
    ./scripts/docker/entry.sh true

    inv_dir='${INVENTORY_DIR}'
    inv_file=\"\${inv_dir}/${TEST_DEPLOY_TYPE}.yml\"
    pw_file=\"\${inv_dir}/.password\"
    echo \">>> Reset inventory dir \${inv_dir}\"
    rm -rf \"\${inv_dir}\"
    mkdir -p \"\${inv_dir}\"
    mkdir -p \"\${inv_dir}\"

    if [[ ! -f \"\${pw_file}\" ]]; then
      printf '%s\n' 'local-vault-password' > \"\${pw_file}\"
      chmod 600 \"\${pw_file}\" || true
    fi

    echo \">>> Creating inventory at \${inv_file}\"
    python3 -m cli.create.inventory \"\${inv_dir}\" \
      --inventory-file \${inv_file} \
      --vars '${RUNTIME_VARS_JSON}' \
      --host 'localhost' \
      --ssl-disabled \
      --vars-file inventory.sample.yml \
      --include '${apps_csv}'

    echo '✅ Inventory initialized.'
  "

echo
echo "✅ Local inventory init finished."
echo "Inventory: ${INVENTORY_DIR}/${TEST_DEPLOY_TYPE}.yml"
