#!/usr/bin/env bash
# Deploy on minimal hardware — disable non-essential services to save resources.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/tests/environment/lib.sh
source "${SCRIPT_DIR}/lib.sh"

echo "Deploying dashboard with matomo disabled to verify SERVICES_DISABLED suppresses the shared service in the inventory."
make deploy-fresh-purged-apps APPS="${DASHBOARD_APP}" SERVICES_DISABLED="matomo"
inspect

echo "Trusting the local CA certificate so HTTPS endpoints are reachable from the host."
make trust-ca

echo "Verifying the dashboard is reachable (matomo was disabled, not the dashboard itself)."
assert_http_status 200 "${DASHBOARD_URL}"

echo "Verifying matomo is not reachable because it was excluded from the inventory."
# Expect 000 because curl aborts in TLS before HTTP when the excluded hostname is missing from the certificate SANs.
assert_http_status 000 "${MATOMO_URL}"
