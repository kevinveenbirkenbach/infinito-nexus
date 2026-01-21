#!/usr/bin/env bash
set -euo pipefail

# SPOT: Deploy exactly ONE app across ALL distros (serial).
#
# Required env:
#   APP="web-app-keycloak"
#   TEST_DEPLOY_TYPE="server|workstation|universal"
#   DISTROS="arch debian ubuntu fedora centos"
#
# Optional env:
#   TESTED_LIFECYCLES="alpha beta rc stable"

# ---------------------------------------------------------------------
# Required env
# ---------------------------------------------------------------------
: "${APP:?APP is required (e.g. APP=web-app-keycloak)}"
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE is required (server|workstation|universal)}"
: "${DISTROS:?DISTROS is required (e.g. 'arch debian ubuntu fedora centos')}"

# ---------------------------------------------------------------------
# Optional env
# ---------------------------------------------------------------------
TESTED_LIFECYCLES="${TESTED_LIFECYCLES:-alpha beta rc stable}"

# Validate deploy type
case "${TEST_DEPLOY_TYPE}" in
  server|workstation|universal) ;;
  *)
    echo "Invalid TEST_DEPLOY_TYPE: ${TEST_DEPLOY_TYPE}" >&2
    echo "Allowed: server | workstation | universal" >&2
    exit 2
    ;;
esac

normalize_bool() {
  case "${1:-}" in
    true|True|TRUE|1) echo "true" ;;
    false|False|FALSE|0) echo "false" ;;
    *)
      echo "Invalid boolean: ${1:-<empty>} (use true/false/1/0)" >&2
      exit 2
      ;;
  esac
}

export TESTED_LIFECYCLES

deploy_type="${TEST_DEPLOY_TYPE}"

mkdir -p logs

read -r -a distro_arr <<< "${DISTROS}"

for distro in "${distro_arr[@]}"; do
  export INFINITO_DISTRO="${distro}"

  log_file="logs/deploy-${TEST_DEPLOY_TYPE}-${distro}-${APP}.log"
  {
    echo "=== $(date -u) ==="
    echo "test_deploy_type=${TEST_DEPLOY_TYPE}"
    echo "deploy_type=${deploy_type}"
    echo "distro=${distro}"
    echo "app=${APP}"
    echo "tested_lifecycles=${TESTED_LIFECYCLES}"
    echo

    echo "--- disk before ---"
    df -h || true
    docker system df || true

    set +e
    args=( --type "${deploy_type}" --app "${APP}" --debug )
    args+=( --keep-stack-on-failure )
    scripts/tests/deploy/ci/distros.sh "${args[@]}"
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

    exit "$rc"
  } 2>&1 | tee "${log_file}"

  rc=${PIPESTATUS[0]}
  if [[ $rc -ne 0 ]]; then
    echo "FAILED: app=${APP} distro=${distro} (see ${log_file})" >&2
    exit "$rc"
  fi
done
