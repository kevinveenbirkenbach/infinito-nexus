#!/usr/bin/env bash
set -euo pipefail

# SPOT: Deploy exactly ONE app on ONE distro, twice, against the same stack.
#
# Flow:
#   1) Ensure compose stack is up (reuse if already running)
#   2) PASS 1:
#        - init inventory with ASYNC_ENABLED=false
#        - deploy (always with --debug)
#   3) PASS 2:
#        - re-init inventory with ASYNC_ENABLED=true
#        - deploy again (same stack)
#   4) Always remove stack so the next distro starts fresh
#
# Required env:
#   INFINITO_DISTRO="arch|debian|ubuntu|fedora|centos"
#   INVENTORY_DIR="/path/to/inventory"
#
# Optional env:
#   PYTHON="python3"

PYTHON="${PYTHON:-python3}"

: "${INFINITO_DISTRO:?INFINITO_DISTRO must be set (e.g. arch)}"
: "${INVENTORY_DIR:?INVENTORY_DIR must be set}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

TYPE=""
APP=""

usage() {
  cat <<'EOF'
Usage:
  INFINITO_DISTRO=<distro> INVENTORY_DIR=<dir> \
    scripts/tests/deploy/ci/dedicated_distro.sh \
    --type <server|workstation|universal> \
    --app <app_id>
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --type) TYPE="${2:-}"; shift 2 ;;
    --app)  APP="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "[ERROR] Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

[[ -n "${TYPE}" ]] || { echo "[ERROR] --type is required" >&2; usage; exit 2; }
[[ -n "${APP}"  ]] || { echo "[ERROR] --app is required"  >&2; usage; exit 2; }

cd "${REPO_ROOT}"

echo "=== distro=${INFINITO_DISTRO} type=${TYPE} app=${APP} (debug always on) ==="

cleanup() {
  rc=$?

  echo ">>> Removing stack for distro ${INFINITO_DISTRO} (fresh start for next distro)"
  "${PYTHON}" -m cli.deploy.development down --distro "${INFINITO_DISTRO}" || true

  echo ">>> HARD cleanup (containers/volumes/networks), keeping images"

  # 1) Remove ALL containers (including running ones)
  ids="$(docker ps -aq || true)"
  if [[ -n "${ids}" ]]; then
    docker rm -f ${ids} >/dev/null 2>&1 || true
  fi

  # 2) Remove networks (except default ones)
  docker network prune -f >/dev/null 2>&1 || true

  # 3) Remove ALL volumes
  docker volume prune -f >/dev/null 2>&1 || true

  # 4) Optional: leftover stopped containers (usually redundant after rm -f)
  docker container prune -f >/dev/null 2>&1 || true

  echo ">>> HARD cleanup finished"
  return $rc
}
trap cleanup EXIT


echo ">>> Ensuring stack is up for distro ${INFINITO_DISTRO}"
"${PYTHON}" -m cli.deploy.development up \
  --distro "${INFINITO_DISTRO}" \
  --when-down

deploy_args=(
  --distro "${INFINITO_DISTRO}"
  --type "${TYPE}"
  --app "${APP}"
  --inventory-dir "${INVENTORY_DIR}"
  --debug
)

echo ">>> DISK / DOCKER STATE BEFORE DEPLOY (distro=${INFINITO_DISTRO})"
df -h || true
docker system df || true
echo ">>> END STATE BEFORE DEPLOY"

echo ">>> PASS 1: init inventory (ASYNC_ENABLED=false)"
"${PYTHON}" -m cli.deploy.development init \
  --distro "${INFINITO_DISTRO}" \
  --app "${APP}" \
  --inventory-dir "${INVENTORY_DIR}" \
  --vars '{"ASYNC_ENABLED": false}'

echo ">>> PASS 1: deploy"
"${PYTHON}" -m cli.deploy.development deploy "${deploy_args[@]}"

echo ">>> PASS 2: re-init inventory (ASYNC_ENABLED=true)"
"${PYTHON}" -m cli.deploy.development init \
  --distro "${INFINITO_DISTRO}" \
  --app "${APP}" \
  --inventory-dir "${INVENTORY_DIR}" \
  --vars '{"ASYNC_ENABLED": true}'

echo ">>> PASS 2: deploy"
"${PYTHON}" -m cli.deploy.development deploy "${deploy_args[@]}"

echo ">>> DISK / DOCKER STATE AFTER DEPLOY (before cleanup, distro=${INFINITO_DISTRO})"
df -h || true
docker system df || true
echo ">>> END STATE AFTER DEPLOY"
