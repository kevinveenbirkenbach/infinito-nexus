#!/usr/bin/env bash
set -euo pipefail

# Purpose (SRP): Return JSON list of apps based on mode + regex filters.
#
# Inputs via env:
#   MODE              = server|workstation|rest
#   INCLUDE_RE         (optional)
#   EXCLUDE_RE         (optional)
#   FINAL_EXCLUDE_RE   (optional)
#
# Output:
#   JSON array to stdout

MODE="${MODE:-server}"
INCLUDE_RE="${INCLUDE_RE:-}"
EXCLUDE_RE="${EXCLUDE_RE:-}"
FINAL_EXCLUDE_RE="${FINAL_EXCLUDE_RE:-}"

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

discover_simple() {
  local include_re="$1"
  local exclude_re="$2"
  INCLUDE_RE="${include_re}" EXCLUDE_RE="${exclude_re}" scripts/tests/discover-apps.sh
}

case "${MODE}" in
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
  rest)
    # rest = all - (server ∪ workstation)
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
    echo "ERROR: MODE must be server|workstation|rest (got: ${MODE})" >&2
    exit 2
    ;;
esac

apps_json="$(apply_final_exclude "${apps_json}" "${FINAL_EXCLUDE_RE}")"
echo "${apps_json}"
