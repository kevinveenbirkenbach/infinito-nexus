#!/usr/bin/env bash
# Prepare a temporary Git repository when CI runs from a snapshot checkout.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/tests/environment/lib.sh
source "${SCRIPT_DIR}/lib.sh"

cd "${REPO_ROOT}"

# CI package/runtime validation can run from a repository snapshot without .git.
# Local development should always use a real checkout, so this fallback stays
# inactive there and only bootstraps the Git context needed for hook testing.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	if ! command -v git >/dev/null 2>&1; then
		echo "[FAIL] git is required to bootstrap the temporary CI test repository." >&2
		exit 1
	fi

	echo "Initializing a temporary Git repository for CI bootstrap validation."
	git init -b main
	git config user.name "CI Bootstrap"
	git config user.email "ci-bootstrap@example.invalid"
	git config commit.gpgsign false
	git add --all .
	git commit -m "test: initialize repository for environment bootstrap"
fi
