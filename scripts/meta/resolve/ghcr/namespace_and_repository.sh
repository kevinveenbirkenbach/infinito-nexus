#!/usr/bin/env bash
# Resolves the GHCR namespace and repository name, then writes both to GITHUB_OUTPUT.
# Usage: GHCR_NAMESPACE_INPUT=<optional> bash namespace_and_repository.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

ghcr_namespace="${GHCR_NAMESPACE_INPUT:-}"
if [[ -n "${ghcr_namespace}" ]]; then
	ghcr_namespace="${ghcr_namespace,,}"
else
	ghcr_namespace="$("${REPO_ROOT}/scripts/meta/resolve/repository/owner.sh")"
fi
ghcr_repository="$("${REPO_ROOT}/scripts/meta/resolve/repository/name.sh")"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
	echo "ghcr_namespace=${ghcr_namespace}" >>"${GITHUB_OUTPUT}"
	echo "ghcr_repository=${ghcr_repository}" >>"${GITHUB_OUTPUT}"
else
	echo "ghcr_namespace=${ghcr_namespace}"
	echo "ghcr_repository=${ghcr_repository}"
fi
