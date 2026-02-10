#!/usr/bin/env bash
set -euo pipefail

# SPOT: Deploy exactly ONE app across ALL distros (serial).
#
# Additionally:
# - Track duration per distro
# - Enforce a global time budget for the whole run (env: MAX_TOTAL_SECONDS)
# - Skip a distro if remaining time is smaller than the max duration of any previous distro run
#
# Required env:
#   APP="web-app-keycloak"
#   TEST_DEPLOY_TYPE="server|workstation|universal"
#   DISTROS="arch debian ubuntu fedora centos"
#   INVENTORY_DIR="/path/to/inventory"
#
# Optional env:
#   PYTHON="python3"
#   MAX_TOTAL_SECONDS="5400"   # global time budget in seconds (empty/undefined = disabled)

: "${APP:?APP is required (e.g. APP=web-app-keycloak)}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE is required (server|workstation|universal)}"
: "${DISTROS:?DISTROS is required (e.g. 'arch debian ubuntu fedora centos')}"
: "${INVENTORY_DIR:?INVENTORY_DIR is required}"
export INVENTORY_DIR

PYTHON="${PYTHON:-python3}"
MAX_TOTAL_SECONDS="${MAX_TOTAL_SECONDS:-}"

if [[ -n "${MAX_TOTAL_SECONDS}" ]]; then
  if ! [[ "${MAX_TOTAL_SECONDS}" =~ ^[0-9]+$ ]]; then
    echo "[ERROR] MAX_TOTAL_SECONDS must be an integer (seconds), got: '${MAX_TOTAL_SECONDS}'" >&2
    exit 2
  fi
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
cd "${REPO_ROOT}"

read -r -a distro_arr <<< "${DISTROS}"
mapfile -t distro_arr < <(printf '%s\n' "${distro_arr[@]}" | shuf)
echo "=== Distro execution order: ${distro_arr[*]} ==="

global_start="$(date +%s)"
deadline=""
if [[ -n "${MAX_TOTAL_SECONDS}" ]]; then
  deadline="$((global_start + MAX_TOTAL_SECONDS))"
  echo "=== Global time budget enabled: ${MAX_TOTAL_SECONDS}s (deadline epoch=${deadline}) ==="
else
  echo "=== Global time budget disabled (set MAX_TOTAL_SECONDS to enable) ==="
fi

max_seen=0
skipped=0
ran=0
failed=0
durations=()  # store "distro=seconds" lines

for distro in "${distro_arr[@]}"; do
  now="$(date +%s)"
  remaining=""

  if [[ -n "${deadline}" ]]; then
    remaining="$((deadline - now))"

    if (( remaining <= 0 )); then
      echo "[WARN] Global budget exhausted (remaining=${remaining}s). Stopping further distro runs."
      break
    fi

    # Skip logic: only if we already have a max_seen from a prior run
    if (( max_seen > 0 && remaining < max_seen )); then
      echo "[WARN] Skipping distro=${distro}: remaining=${remaining}s < max_seen=${max_seen}s (fast-fail heuristic)"
      skipped=$((skipped + 1))
      continue
    fi
  fi

  echo "=== Running dedicated distro deploy: distro=${distro} app=${APP} type=${TEST_DEPLOY_TYPE} ==="
  if [[ -n "${remaining}" ]]; then
    echo ">>> Time budget: remaining=${remaining}s max_seen=${max_seen}s"
  fi

  export INFINITO_DISTRO="${distro}"

  distro_start="$(date +%s)"

  set +e
  scripts/tests/deploy/ci/dedicated_distro.sh \
    --app "${APP}"
  rc=$?
  set -e

  distro_end="$(date +%s)"
  dur="$((distro_end - distro_start))"
  durations+=("${distro}=${dur}s")
  ran=$((ran + 1))

  if (( dur > max_seen )); then
    max_seen="$dur"
  fi

  echo ">>> Duration: distro=${distro} took ${dur}s (max_seen=${max_seen}s)"

  if [[ $rc -ne 0 ]]; then
    echo "[ERROR] Deploy failed for distro=${distro} app=${APP} (rc=${rc})" >&2
    failed=$((failed + 1))
    exit "$rc"
  fi
done

global_end="$(date +%s)"
total="$((global_end - global_start))"

echo
echo "=== Summary ==="
echo "app=${APP} type=${TEST_DEPLOY_TYPE}"
echo "ran=${ran} skipped=${skipped} failed=${failed}"
echo "total_runtime=${total}s max_seen_distro=${max_seen}s"
if [[ -n "${deadline}" ]]; then
  now="$(date +%s)"
  remaining="$((deadline - now))"
  echo "budget=${MAX_TOTAL_SECONDS}s remaining=${remaining}s"
fi
echo "per-distro:"
for line in "${durations[@]}"; do
  echo "  - ${line}"
done
