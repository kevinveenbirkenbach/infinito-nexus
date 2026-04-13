#!/usr/bin/env bash
# scripts/github/output_apps.sh
#
# Resolve the app list and write it to GITHUB_OUTPUT.
# Inputs via env (forwarded to scripts/meta/resolve/apps.sh):
#   TEST_DEPLOY_TYPE  — required (server|workstation|universal)
#   WHITELIST         — optional space-separated allowlist
set -euo pipefail

apps="$(./scripts/meta/resolve/apps.sh)"
[[ -n "$apps" ]] || apps='[]'

echo "apps=$apps" >>"$GITHUB_OUTPUT"
echo "apps_json=$apps" >>"$GITHUB_OUTPUT"
echo "apps_json=$apps"
