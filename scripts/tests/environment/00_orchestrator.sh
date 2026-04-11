#!/usr/bin/env bash
# Orchestrates the full local Infinito.Nexus environment test suite.
# Serves as a reference for how to deploy and debug applications locally.
set -euo pipefail

# Force local runtime context.
unset GITHUB_ACTIONS
unset ACT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/tests/environment/lib.sh
source "${SCRIPT_DIR}/lib.sh"

# pkgmgr images may reset the working directory before invoking this script.
cd "${REPO_ROOT}"

for step in "${SCRIPT_DIR}"/[0-9][0-9]_*.sh; do
	[[ "${step}" == "${BASH_SOURCE[0]}" ]] && continue
	load_repo_env
	ensure_git_safe_directory
	echo "============================================================"
	echo ">>> $(basename "${step}")"
	echo "============================================================"
	bash "${step}"
done
