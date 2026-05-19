#!/usr/bin/env bash
# Deploy on performance hardware — deploy the full set of applications.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/tests/environment/utils/common.sh
source "${SCRIPT_DIR}/utils/common.sh"

echo "Deploying matomo (full cycle: deploy + update pass) so it becomes reachable via its dedicated inventory entry."
make deploy-fresh-purged-apps APPS="${MATOMO_APP}" FULL_CYCLE=true
inspect

echo "Re-trusting the CA after the fresh deploy rebuilt the certificates."
make trust-ca

echo "Verifying matomo is now reachable after its dedicated deploy."
assert_http_status 200 "${MATOMO_URL}"

echo "Verifying the dashboard is no longer reachable after the matomo-only fresh deploy."
# 421 = Misdirected Request: cert SAN still covers the host but no vhost is configured.
assert_http_status 421 "${DASHBOARD_URL}"
