#!/usr/bin/env bash
# Resolve the local Docker image tag for the current repository and distro.
# Output format: <repo-basename>/<distro>
# This is the SPOT for the local image name used by both build and compose.
set -euo pipefail

repo_name="$(bash "$(dirname "${BASH_SOURCE[0]}")/../repository/name.sh")"
distro="${INFINITO_DISTRO:-debian}"

printf '%s/%s\n' "${repo_name}" "${distro}"
