#!/usr/bin/env bash
# scripts/meta/build-test-matrix.sh (vollständig, final)
set -euo pipefail

# Purpose (SRP): Return JSON list of apps based on mode + regex filters.
#
# Inputs via env:
#   TEST_DEPLOY_TYPE              = server|workstation|universal (required)
#   FINAL_EXCLUDE_RE   (optional)
#
# Output:
#   JSON array to stdout

: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE is required (server|workstation|universal)}"

FINAL_EXCLUDE_RE="${FINAL_EXCLUDE_RE:-}"

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

  # Extract roles into bash array
  mapfile -t roles < <(echo "${apps_json}" | jq -r '.[]')
  if [[ "${#roles[@]}" -eq 0 ]]; then
    echo "${apps_json}"
    return 0
  fi

  # 1) Warnings run (show what gets filtered)
  # We do NOT want to change the JSON output of discover.sh, so we discard this stdout.
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

  # Convert back to JSON
  if [[ -z "${kept}" ]]; then
    echo "[]"
    return 0
  fi

  # shellcheck disable=SC2086
  printf "%s\n" ${kept} | jq -R -s -c 'split("\n") | map(select(length>0))'
}

case "${TEST_DEPLOY_TYPE}" in
  server|workstation|universal)
    apps_json="$(
      docker compose --profile ci exec -T infinito \
        "${PYTHON}" -m cli.meta.applications.type --format json --type "${TEST_DEPLOY_TYPE}"
    )"
    # Ensure non-empty JSON array
    [[ -n "${apps_json}" ]] || apps_json="[]"
    ;;
  *)
    echo "ERROR: TEST_DEPLOY_TYPE must be server|workstation|universal (got: ${TEST_DEPLOY_TYPE})" >&2
    exit 2
    ;;
esac

# Keep legacy exclusion for this one role (previously only applied to universal)
if [[ "${TEST_DEPLOY_TYPE}" == "universal" ]]; then
  apps_json="$(apply_final_exclude "${apps_json}" '^(web-opt-rdr-www)$')"
fi

apps_json="$(filter_by_ci_storage "${apps_json}")"
apps_json="$(apply_final_exclude "${apps_json}" "${FINAL_EXCLUDE_RE}")"
echo "${apps_json}"
