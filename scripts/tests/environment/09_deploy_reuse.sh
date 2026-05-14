#!/usr/bin/env bash
# Redeploy keeping inventory and apt packages — validates reuse of existing state.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/tests/environment/utils/common.sh
source "${SCRIPT_DIR}/utils/common.sh"

echo "Redeploying matomo (variant 0) while keeping inventory and packages to validate state reuse."
make deploy-reuse-kept-apps APPS="${MATOMO_APP}" VARIANT=0
inspect
