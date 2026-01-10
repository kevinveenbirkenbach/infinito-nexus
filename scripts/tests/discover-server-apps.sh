#!/usr/bin/env bash
set -euo pipefail

# Discovers invokable server apps from inside the running infinito container.
# Output: JSON array, e.g. ["web-app-foo","web-svc-bar"]
#
# Requires:
# - docker compose stack running (profile "ci") with service "infinito"
# - jq installed on the runner
#
# Lifecycle gating:
# - Uses TESTED_LIFECYCLES (space or comma-separated)
# - Default: "alpha beta rc stable"

# 1) Get invokable roles from container (one per line)
invokable="$(
  docker compose --profile ci exec -T infinito \
    python3 -m cli.meta.applications.invokable \
  | sed -e 's/[[:space:]]\+$//' -e '/^$/d'
)"

# 2) Keep only server apps
filtered="$(printf "%s\n" "${invokable}" | grep -E '^(web-app-|web-svc-)' || true)"

# 3) Convert to JSON array
apps_json="$(
  printf "%s\n" "${filtered}" \
  | jq -R -s -c 'split("\n") | map(select(length>0))'
)"

# 4) Apply lifecycle gating (blacklist mode: exclude roles NOT in tested lifecycles)
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
