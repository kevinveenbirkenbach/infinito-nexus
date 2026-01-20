#!/usr/bin/env bash
set -euo pipefail

# Purpose (SRP): Return JSON list of apps based on mode + regex filters.
#
# Inputs via env:
#   TEST_DEPLOY_TYPE              = server|workstation|universal
#   INCLUDE_RE         (optional)
#   EXCLUDE_RE         (optional)
#   FINAL_EXCLUDE_RE   (optional)
#
# Output:
#   JSON array to stdout
TEST_DEPLOY_TYPE="${TEST_DEPLOY_TYPE:-server}"
INCLUDE_RE="${INCLUDE_RE:-}"
EXCLUDE_RE="${EXCLUDE_RE:-}"
FINAL_EXCLUDE_RE="${FINAL_EXCLUDE_RE:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

json_nonempty() {
  local j="${1:-}"
  [[ -n "${j}" ]] || j='[]'
  echo "${j}"
}

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
    python3 -m cli.meta.applications.sufficient_storage \
      --roles "${roles[@]}" \
      --required-storage "${required_storage}" \
      --warnings \
      >/dev/null || true

  kept="$(
    docker compose --profile ci exec -T infinito \
      python3 -m cli.meta.applications.sufficient_storage \
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

discover_simple() {
  local include_re="$1"
  local exclude_re="$2"
  INCLUDE_RE="${include_re}" EXCLUDE_RE="${exclude_re}" scripts/tests/discover-apps.sh
}

case "${TEST_DEPLOY_TYPE}" in
  server)
    : "${INCLUDE_RE:=^(web-app-|web-svc-)}"
    : "${EXCLUDE_RE:=^(web-app-oauth2-proxy)$}"
    apps_json="$(discover_simple "${INCLUDE_RE}" "${EXCLUDE_RE}")"
    apps_json="$(json_nonempty "${apps_json}")"
    ;;
  workstation)
    : "${INCLUDE_RE:=^(desk-|util-desk-)}"
    : "${EXCLUDE_RE:=}"
    apps_json="$(discover_simple "${INCLUDE_RE}" "${EXCLUDE_RE}")"
    apps_json="$(json_nonempty "${apps_json}")"
    ;;
  universal)
    # universal = all - (server ∪ workstation)
    all_json="$(discover_simple '.*' '')"
    all_json="$(json_nonempty "${all_json}")"

    server_json="$(discover_simple '^(web-app-|web-svc-)' '^(web-app-oauth2-proxy)$')"
    server_json="$(json_nonempty "${server_json}")"

    workstation_json="$(discover_simple '^(desk-|util-desk-)' '')"
    workstation_json="$(json_nonempty "${workstation_json}")"

    apps_json="$(
      jq -nc \
        --argjson all "${all_json}" \
        --argjson server "${server_json}" \
        --argjson workstation "${workstation_json}" \
        '
          def uniq: unique;
          def union($a;$b): ($a + $b) | uniq;
          def minus($a;$b): $a | map(select(. as $x | ($b | index($x)) | not));

          (union($server; $workstation) | uniq) as $covered
          | minus($all; $covered)
          | unique
        '
    )"
    ;;
  *)
    echo "ERROR: TEST_DEPLOY_TYPE must be server|workstation|universal (got: ${TEST_DEPLOY_TYPE})" >&2
    exit 2
    ;;
esac
apps_json="$(filter_by_ci_storage "${apps_json}")"
apps_json="$(apply_final_exclude "${apps_json}" "${FINAL_EXCLUDE_RE}")"
echo "${apps_json}"
