#!/usr/bin/env bash
# Orchestrates the full local Infinito.Nexus environment test suite.
# Serves as a reference for how to deploy and debug applications locally.
set -euo pipefail

# Force local runtime context.
unset GITHUB_ACTIONS
unset ACT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Resolve to an absolute path so the self-exclusion works regardless of whether
# the script was invoked with a relative path (e.g. bash ./scripts/…/00_orchestrator.sh).
SELF="${SCRIPT_DIR}/$(basename "${BASH_SOURCE[0]}")"
# shellcheck source=scripts/tests/environment/utils/common.sh
source "${SCRIPT_DIR}/utils/common.sh"

# pkgmgr images may reset the working directory before invoking this script.
cd "${REPO_ROOT}"

for step in "${SCRIPT_DIR}"/[0-9][0-9]_*.sh; do
	[[ "${step}" == "${SELF}" ]] && continue
	load_repo_env
	ensure_git_safe_directory
	echo "============================================================"
	echo ">>> $(basename "${step}")"
	echo "============================================================"
	bash "${step}"
done
