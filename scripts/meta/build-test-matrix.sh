#!/usr/bin/env bash
# scripts/meta/build-test-matrix.sh
set -euo pipefail

# Purpose (SRP): Return JSON list of apps based on deployment type,
# optionally filtered by lifecycle and CI storage constraints.
#
# Inputs via env:
#   TEST_DEPLOY_TYPE   = server|workstation|universal (required)
#   TESTED_LIFECYCLES  = space-separated list (optional)
#   FINAL_EXCLUDE_RE   = optional grep -Ev regex
#
# Output:
#   JSON array to stdout

: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE is required (server|workstation|universal)}"

FINAL_EXCLUDE_RE="${FINAL_EXCLUDE_RE:-}"
TESTED_LIFECYCLES="${TESTED_LIFECYCLES:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

apply_final_exclude() {
  local apps_json="$1"
  local final_excl="$2"

  if [[ -z "${final_excl}" ]]; then
    echo "${apps_json}"
    return 0
  fi

  local txt
  txt="$(echo "${apps_json}" | jq -r '.[]' | grep -Ev "${final_excl}" || true)"

  printf "%s\n" "${txt}" \
    | jq -R -s -c 'split("\n") | map(select(length>0))'
}

filter_by_ci_storage() {
  local apps_json="$1"

  # Only enforce on GitHub Actions, but NOT in act
  if [[ -z "${GITHUB_ACTIONS:-}" || -n "${ACT:-}" ]]; then
    echo "${apps_json}"
    return 0
  fi

  local required_storage="${CI_REQUIRED_STORAGE:-60GB}"

  mapfile -t roles < <(echo "${apps_json}" | jq -r '.[]')
  if [[ "${#roles[@]}" -eq 0 ]]; then
    echo "${apps_json}"
    return 0
  fi

  docker compose --profile ci exec -T infinito \
    "${PYTHON}" -m cli.meta.applications.sufficient_storage \
      --roles "${roles[@]}" \
      --required-storage "${required_storage}" \
      --warnings \
      >/dev/null || true

  kept="$(
    docker compose --profile ci exec -T infinito \
      "${PYTHON}" -m cli.meta.applications.sufficient_storage \
        --roles "${roles[@]}" \
        --required-storage "${required_storage}"
  )"

  if [[ -z "${kept}" ]]; then
    echo "[]"
    return 0
  fi

  printf "%s\n" "${kept}" \
    | jq -R -s -c 'split("\n") | map(select(length>0))'
}

# ------------------------------------------------------------
# Lifecycle handling (SC2086-safe)
# ------------------------------------------------------------
lifecycles_args=()
if [[ -n "${TESTED_LIFECYCLES}" ]]; then
  read -r -a lifecycles_arr <<< "${TESTED_LIFECYCLES}"
  lifecycles_args=(--lifecycles "${lifecycles_arr[@]}")
fi

case "${TEST_DEPLOY_TYPE}" in
  server|workstation|universal)
    apps_json="$(
      docker compose --profile ci exec -T infinito \
        "${PYTHON}" -m cli.meta.applications.type \
          --format json \
          --type "${TEST_DEPLOY_TYPE}" \
          "${lifecycles_args[@]}"
    )"
    [[ -n "${apps_json}" ]] || apps_json="[]"
    ;;
  *)
    echo "ERROR: TEST_DEPLOY_TYPE must be server|workstation|universal (got: ${TEST_DEPLOY_TYPE})" >&2
    exit 2
    ;;
esac

# ------------------------------------------------------------
# Global hard excludes (never tested / deployed)
# ------------------------------------------------------------
apps_json="$(apply_final_exclude "${apps_json}" '^(web-opt-rdr-www|web-app-oauth2-proxy)$')"

# CI storage + user-defined excludes
apps_json="$(filter_by_ci_storage "${apps_json}")"
apps_json="$(apply_final_exclude "${apps_json}" "${FINAL_EXCLUDE_RE}")"

echo "${apps_json}"
