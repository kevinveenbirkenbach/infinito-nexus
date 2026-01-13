#!/usr/bin/env bash
set -euo pipefail

# SPOT: Deploy exactly ONE app across ALL distros (serial).
#
# Required env:
#   APP="web-app-keycloak"
#   MODE="server|workstation|rest"
#   DISTROS="arch debian ubuntu fedora centos"
#
# Optional env:
#   TESTED_LIFECYCLES="alpha beta rc stable"
#   MISSING_ONLY="true|false"
#   KEEP_STACK="true|false"

APP="${APP:-}"
MODE="${MODE:-server}"
DISTROS="${DISTROS:-arch debian ubuntu fedora centos}"

TESTED_LIFECYCLES="${TESTED_LIFECYCLES:-alpha beta rc stable}"
MISSING_ONLY="${MISSING_ONLY:-true}"
KEEP_STACK="${KEEP_STACK:-true}"

[[ -n "${APP}" ]] || { echo "ERROR: APP is required"; exit 2; }

normalize_bool() {
  case "${1:-}" in
    true|True|TRUE|1) echo "true" ;;
    false|False|FALSE|0) echo "false" ;;
    *) echo "true" ;;
  esac
}

MISSING_ONLY="$(normalize_bool "${MISSING_ONLY}")"
KEEP_STACK="$(normalize_bool "${KEEP_STACK}")"

export TESTED_LIFECYCLES

deploy_type="${MODE}"
if [[ "${MODE}" == "rest" ]]; then
  deploy_type="server"
fi

mkdir -p logs

read -r -a distro_arr <<< "${DISTROS}"

for distro in "${distro_arr[@]}"; do
  export INFINITO_DISTRO="${distro}"

  log_file="logs/deploy-${MODE}-${distro}-${APP}.log"
  {
    echo "=== $(date -u) ==="
    echo "mode=${MODE}"
    echo "deploy_type=${deploy_type}"
    echo "distro=${distro}"
    echo "app=${APP}"
    echo "tested_lifecycles=${TESTED_LIFECYCLES}"
    echo "missing_only=${MISSING_ONLY}"
    echo "keep_stack=${KEEP_STACK}"
    echo

    echo "--- disk before ---"
    df -h || true
    docker system df || true

    set +e
    args=( --type "${deploy_type}" --app "${APP}" )
    if [[ "${MISSING_ONLY}" == "true" ]]; then args+=( --missing ); fi
    if [[ "${KEEP_STACK}" == "true" ]]; then args+=( --keep-stack-on-failure ); fi
    scripts/tests/deploy.sh "${args[@]}"
    rc=$?
    set -e

    echo
    echo "--- disk after ---"
    df -h || true
    docker system df || true

    if [[ $rc -eq 0 ]]; then
      echo "--- cleanup (success) ---"
      docker system prune -af --volumes || true
      docker builder prune -af || true
    else
      echo "--- no cleanup (failure) ---"
    fi

    exit $rc
  } 2>&1 | tee "${log_file}"

  rc=${PIPESTATUS[0]}
  if [[ $rc -ne 0 ]]; then
    echo "FAILED: app=${APP} distro=${distro} (see ${log_file})" >&2
    exit $rc
  fi
done
