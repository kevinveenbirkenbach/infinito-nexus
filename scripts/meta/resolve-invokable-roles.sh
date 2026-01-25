#!/usr/bin/env bash
set -euo pipefail

# Generic discover script for invokable roles inside the running infinito container.
#
# Output: JSON array, e.g. ["web-app-foo","web-svc-bar"]
#
# Requires:
# - docker compose stack running (profile "ci") with service "infinito"
# - jq installed on the runner
#
# Filtering:
# - INCLUDE_RE: grep -E regex applied first (default: keep everything)
# - EXCLUDE_RE: grep -Ev regex applied after include (default: exclude nothing)
#
# Lifecycle gating:
# - Uses TESTED_LIFECYCLES (space or comma-separated)
# - Default: "alpha beta rc stable"
#
# Examples:
#   # server apps
#   INCLUDE_RE='^(web-app-|web-svc-)' scripts/meta/resolve-invokable-roles.sh
#
#   # workstation apps
#   INCLUDE_RE='^(desk-|util-desk-)' scripts/meta/resolve-invokable-roles.sh
#
#   # server apps but exclude known flaky
#   INCLUDE_RE='^(web-app-|web-svc-)' EXCLUDE_RE='^(web-app-oauth2-proxy)$' scripts/meta/resolve-invokable-roles.sh

INCLUDE_RE="${INCLUDE_RE:-.*}"
EXCLUDE_RE="${EXCLUDE_RE:-}"

# 1) Get invokable roles from container (one per line)
invokable="$(
  docker compose --profile ci exec -T infinito \
    "${PYTHON}" -m cli.meta.applications.invokable \
  | sed -e 's/[[:space:]]\+$//' -e '/^$/d'
)"

# 2) Include filter
filtered="$(
  printf "%s\n" "${invokable}" | grep -E "${INCLUDE_RE}" || true
)"

# 3) Exclude filter (optional, applied after include)
if [[ -n "${EXCLUDE_RE}" ]]; then
  filtered="$(
    printf "%s\n" "${filtered}" | grep -Ev "${EXCLUDE_RE}" || true
  )"
fi

# 4) Convert to JSON array
apps_json="$(
  printf "%s\n" "${filtered}" \
  | jq -R -s -c 'split("\n") | map(select(length>0))'
)"

# 5) Apply lifecycle gating (blacklist mode: exclude roles NOT in tested lifecycles)
tested="${TESTED_LIFECYCLES:-alpha beta rc stable}"
tested="${tested//,/ }"
tested="$(printf "%s\n" "${tested}" | xargs)"

# lifecycle_filter prints role names space-separated (or nothing)
exclude_txt="$(
  docker compose --profile ci exec -T infinito \
    sh -lc "python3 -m cli.meta.roles.lifecycle_filter blacklist ${tested} || true"
)"

exclude_json="$(
  printf "%s\n" "${exclude_txt}" \
  | tr ' ' '\n' \
  | sed -e 's/[[:space:]]\+$//' -e '/^$/d' \
  | jq -R -s -c 'split("\n") | map(select(length>0))'
)"

# Remove excluded roles from apps_json
apps_json="$(
  jq -c --argjson excl "${exclude_json}" \
    'map(select(. as $a | ($excl | index($a)) | not))' \
    <<< "${apps_json}"
)"

# Always output valid JSON
printf "%s\n" "${apps_json}"
