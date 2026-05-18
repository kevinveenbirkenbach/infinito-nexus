#!/usr/bin/env bash
set -euo pipefail

# Reuse-kept redeploy of all apps cumulated from one or more inventory bundles.
#
# Usage:
#   BUNDLES="education-suite,startup-essentials" make redeploy-bundles
#
# Behavior:
#   - Aggregates and deduplicates all role groups declared in each bundle's
#     inventory.yml (see utils.inventory.bundle_apps).
#   - Exports APPS=<csv> and delegates to reuse-kept-app.sh.
#   - Does NOT bring the stack down/up and does NOT purge entities.
#   - Requires an already-initialized inventory (see deploy-bundles or
#     deploy-fresh-kept-apps for the first run).
#
# Required env:
#   BUNDLES            comma-separated bundle names
# Optional env (forwarded to reuse-kept-app.sh):
#   DEBUG              true (default) | false
#   INFINITO_DISTRO    arch|debian|ubuntu|fedora|centos
#   INVENTORY_DIR      /etc/inventories/local-full-server (typical)
#   TEST_DEPLOY_TYPE   server|workstation|universal
#   VARIANT            matrix round index to pin redeploy to

: "${BUNDLES:?BUNDLES must be set (e.g. BUNDLES=education-suite,startup-essentials)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"
cd "${REPO_ROOT}"

PYTHON="${PYTHON:-python3}"
export DEBUG="${DEBUG:-true}"

echo "=== resolving bundles: ${BUNDLES} ==="

APPS="$("${PYTHON}" -m utils.inventory.bundle_apps "${BUNDLES}")"
export APPS

echo "apps  = ${APPS}"
echo "debug = ${DEBUG}"
echo

exec bash "${SCRIPT_DIR}/reuse-kept-app.sh"
