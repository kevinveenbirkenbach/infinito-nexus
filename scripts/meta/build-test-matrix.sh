#!/usr/bin/env bash
# scripts/meta/build-test-matrix.sh
set -euo pipefail

# Purpose (SRP): Return JSON list of apps based on deployment type,
# optionally filtered by lifecycle and CI storage constraints.
#
# Inputs via env:
#   TEST_DEPLOY_TYPE   = server|workstation|universal (required)
#   TESTED_LIFECYCLES  = space-separated list (optional)
#   FINAL_EXCLUDE_RE   = optional grep -Ev regex (applied as regex in jq)
#
# Output:
#   JSON array to stdout (single line, always valid)

: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE is required (server|workstation|universal)}"

FINAL_EXCLUDE_RE="${FINAL_EXCLUDE_RE:-}"
TESTED_LIFECYCLES="${TESTED_LIFECYCLES:-}"
PYTHON="${PYTHON:-python3}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# ------------------------------------------------------------
# Helpers (JSON-only, no text roundtrips)
# ------------------------------------------------------------

json_compact_array() {
  # Read JSON from stdin, ensure it's an array, output compact single-line JSON.
  jq -c 'if type=="array" then . else [] end'
}

jq_exclude_regex() {
  # Args: regex
  # Reads JSON array from stdin, filters out entries matching regex, outputs compact JSON.
  local re="$1"
  if [[ -z "${re}" ]]; then
    json_compact_array
    return 0
  fi
  jq -c --arg re "${re}" 'map(select(test($re) | not))'
}

# ------------------------------------------------------------
# Lifecycle handling (SC2086-safe)
# ------------------------------------------------------------
lifecycles_args=()
if [[ -n "${TESTED_LIFECYCLES}" ]]; then
  read -r -a lifecycles_arr <<< "${TESTED_LIFECYCLES}"
  lifecycles_args=(--lifecycles "${lifecycles_arr[@]}")
fi

# ------------------------------------------------------------
# 1) Get JSON list from container (keep as JSON)
# ------------------------------------------------------------
apps_json="$(
  docker compose --profile ci exec -T infinito \
    "${PYTHON}" -m cli.meta.applications.type \
      --format json \
      --type "${TEST_DEPLOY_TYPE}" \
      "${lifecycles_args[@]}" \
  | json_compact_array
)"

# ------------------------------------------------------------
# 2) Global hard excludes (regex over app ids)
# ------------------------------------------------------------
apps_json="$(
  printf '%s\n' "${apps_json}" \
  | jq_exclude_regex '^(web-opt-rdr-www|web-app-oauth2-proxy)$'
)"

# ------------------------------------------------------------
# 3) CI storage filter (still JSON-safe)
#    NOTE: sufficient_storage currently outputs TEXT (one role per line).
#    We convert that text to JSON array safely without whitespace collapsing.
# ------------------------------------------------------------
if [[ -n "${GITHUB_ACTIONS:-}" && -z "${ACT:-}" ]]; then
  required_storage="60GB"

  # Extract roles from JSON to pass as args (safe: one per line -> bash array)
  mapfile -t roles < <(printf '%s\n' "${apps_json}" | jq -r '.[]')
  if [[ "${#roles[@]}" -gt 0 ]]; then
    docker compose --profile ci exec -T infinito \
      "${PYTHON}" -m cli.meta.applications.sufficient_storage \
        --roles "${roles[@]}" \
        --required-storage "${required_storage}" \
        --warnings \
      >/dev/null || true

    kept_txt="$(
      docker compose --profile ci exec -T infinito \
        "${PYTHON}" -m cli.meta.applications.sufficient_storage \
          --roles "${roles[@]}" \
          --required-storage "${required_storage}" \
      | sed -e 's/[[:space:]]\+$//' -e '/^$/d'
    )"

    if [[ -z "${kept_txt}" ]]; then
      apps_json='[]'
    else
      # Convert "one per line" to JSON array WITHOUT joining by spaces.
      apps_json="$(
        printf '%s\n' "${kept_txt}" \
        | jq -R -s -c 'split("\n") | map(select(length>0))'
      )"
    fi
  fi
fi

# ------------------------------------------------------------
# 4) User-defined FINAL_EXCLUDE_RE (regex)
# ------------------------------------------------------------
apps_json="$(
  printf '%s\n' "${apps_json}" \
  | jq_exclude_regex "${FINAL_EXCLUDE_RE}"
)"

# ------------------------------------------------------------
# 5) Final safety: compact JSON array, single line
# ------------------------------------------------------------
printf '%s\n' "${apps_json}" | json_compact_array
