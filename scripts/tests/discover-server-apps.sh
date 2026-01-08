#!/usr/bin/env bash
set -euo pipefail

# Discovers invokable server apps from inside the running infinito container.
# Output: JSON array, e.g. ["web-app-foo","web-svc-bar"]
#
# Requires:
# - docker compose stack running (profile "ci") with service "infinito"
# - jq installed on the runner

invokable="$(
  docker compose --profile ci exec -T infinito \
    python3 -m cli.meta.applications.invokable \
  | sed -e 's/[[:space:]]\+$//' -e '/^$/d'
)"

# If grep finds nothing it exits 1 -> don't fail discovery
filtered="$(printf "%s\n" "${invokable}" | grep -E '^(web-app-|web-svc-)' || true)"

# Always output valid JSON
printf "%s\n" "${filtered}" \
  | jq -R -s -c 'split("\n") | map(select(length>0))'
