#!/usr/bin/env bash
set -euo pipefail

# One-off deploy of all apps cumulated from one or more inventory bundles.
#
# Usage:
#   BUNDLES="education-suite,startup-essentials" make deploy-bundles
#
# Behavior:
#   - Aggregates and deduplicates all role groups declared in each bundle's
#     inventory.yml (see utils.inventory.bundle_apps).
#   - Exports APPS=<csv> and delegates to fresh-purged-app.sh.
#   - Defaults FULL_CYCLE=false (override by exporting FULL_CYCLE=true).
#
# Required env:
#   BUNDLES            comma-separated bundle names
# Optional env (forwarded to fresh-purged-app.sh):
#   FULL_CYCLE         false (default) | true
#   INFINITO_DISTRO    arch|debian|ubuntu|fedora|centos
#   INVENTORY_DIR      /etc/inventories/local-full-server (typical)
#   TEST_DEPLOY_TYPE   server|workstation|universal

: "${BUNDLES:?BUNDLES must be set (e.g. BUNDLES=education-suite,startup-essentials)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"
cd "${REPO_ROOT}"

PYTHON="${PYTHON:-python3}"
export FULL_CYCLE="${FULL_CYCLE:-false}"

echo "=== resolving bundles: ${BUNDLES} ==="

APPS="$("${PYTHON}" -m utils.inventory.bundle_apps "${BUNDLES}")"
export APPS

echo "apps        = ${APPS}"
echo "full_cycle  = ${FULL_CYCLE}"
echo

exec bash "${SCRIPT_DIR}/fresh-purged-app.sh"
