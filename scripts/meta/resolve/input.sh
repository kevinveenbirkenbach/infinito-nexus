#!/usr/bin/env bash
set -euo pipefail

# Resolve effective workflow parameters (STRICT MODE)
#
# Required:
#   TEST_DEPLOY_TYPE   (server|workstation|universal)
#   DISTROS            (space-separated distro list, e.g. "arch debian")
#
# Always defined:
#   ONLY_APP           (may be empty, but will always be set)
#
# Provided either via:
#   - act --env
#   - workflow_dispatch inputs (forwarded as INPUT_*)
#
# Writes:
#   - to $GITHUB_OUTPUT: test_deploy_type, distros, only_app
#   - to $GITHUB_ENV:   TEST_DEPLOY_TYPE, DISTROS, ONLY_APP

: "${GITHUB_OUTPUT:?GITHUB_OUTPUT must be set (running inside GitHub Actions or act)}"
: "${GITHUB_ENV:?GITHUB_ENV must be set (running inside GitHub Actions or act)}"

# Priority:
#   1) real env
#   2) workflow inputs (passed via env by workflow step)
TEST_DEPLOY_TYPE="${TEST_DEPLOY_TYPE:-${INPUT_TEST_DEPLOY_TYPE:-}}"
DISTROS="${DISTROS:-${INPUT_DISTROS:-}}"

# ONLY_APP is special: must always exist, but may be empty
ONLY_APP="${ONLY_APP:-${INPUT_ONLY_APP:-}}"
ONLY_APP="${ONLY_APP:-}"  # force defined even if still empty

# Hard requirements
: "${TEST_DEPLOY_TYPE:?TEST_DEPLOY_TYPE must be set (server|workstation|universal)}"
: "${DISTROS:?DISTROS must be set (e.g. \"arch debian ubuntu\")}"

case "${TEST_DEPLOY_TYPE}" in
  server|workstation|universal) ;;
  *)
    echo "Invalid TEST_DEPLOY_TYPE: ${TEST_DEPLOY_TYPE}" >&2
    echo "Allowed: server | workstation | universal" >&2
    exit 2
    ;;
esac

echo "Resolved inputs:"
echo "  TEST_DEPLOY_TYPE=${TEST_DEPLOY_TYPE}"
echo "  DISTROS=${DISTROS}"
echo "  ONLY_APP=${ONLY_APP}"

# Export outputs for workflow
{
  echo "test_deploy_type=${TEST_DEPLOY_TYPE}"
  echo "distros=${DISTROS}"
  echo "only_app=${ONLY_APP}"
} >> "${GITHUB_OUTPUT}"

# Export env for subsequent steps
{
  echo "TEST_DEPLOY_TYPE=${TEST_DEPLOY_TYPE}"
  echo "DISTROS=${DISTROS}"
  echo "ONLY_APP=${ONLY_APP}"
} >> "${GITHUB_ENV}"
