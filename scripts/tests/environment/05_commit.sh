#!/usr/bin/env bash
# Validate pre-commit hook enforcement and --no-verify bypass.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/tests/environment/lib.sh
source "${SCRIPT_DIR}/lib.sh"

cd "${REPO_ROOT}"

ORIGINAL_GIT_USER_NAME="$(git config --local --get user.name || true)"
ORIGINAL_GIT_USER_EMAIL="$(git config --local --get user.email || true)"

if [[ -z "${ORIGINAL_GIT_USER_NAME}" ]]; then
	git config --local user.name "Environment Test"
fi

if [[ -z "${ORIGINAL_GIT_USER_EMAIL}" ]]; then
	git config --local user.email "environment-test@example.invalid"
fi

if ORIGINAL_REF="$(git symbolic-ref --quiet --short HEAD)"; then
	:
else
	ORIGINAL_REF="$(git rev-parse --verify HEAD)"
fi

TEST_BRANCH="test/pre-commit-hook-$(date +%s)"
WORKTREE_STASH=""

if [[ -n "$(git status --short)" ]]; then
	WORKTREE_STASH="environment-pre-commit-hook-$(date +%s)"
	echo "Stashing existing repository changes before commit hook validation."
	git stash push --include-untracked --message "${WORKTREE_STASH}" >/dev/null
fi

cleanup() {
	local exit_code="$1"
	set +e

	if git rev-parse --verify "${TEST_BRANCH}" >/dev/null 2>&1; then
		local current_ref
		current_ref="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
		if [[ "${current_ref}" == "${TEST_BRANCH}" ]]; then
			git reset --hard HEAD >/dev/null 2>&1 || true
			git clean -fd >/dev/null 2>&1 || true
			git checkout "${ORIGINAL_REF}" >/dev/null 2>&1 || true
		fi
		git branch -D "${TEST_BRANCH}" >/dev/null 2>&1 || true
	fi

	if [[ -n "${ORIGINAL_GIT_USER_NAME}" ]]; then
		git config --local user.name "${ORIGINAL_GIT_USER_NAME}" >/dev/null 2>&1 || true
	else
		git config --local --unset user.name >/dev/null 2>&1 || true
	fi

	if [[ -n "${ORIGINAL_GIT_USER_EMAIL}" ]]; then
		git config --local user.email "${ORIGINAL_GIT_USER_EMAIL}" >/dev/null 2>&1 || true
	else
		git config --local --unset user.email >/dev/null 2>&1 || true
	fi

	if [[ -n "${WORKTREE_STASH}" ]] && git stash list | grep -F "${WORKTREE_STASH}" >/dev/null 2>&1; then
		if ! git stash pop --index >/dev/null 2>&1; then
			echo "[FAIL] Failed to restore the stashed repository changes after commit validation." >&2
			exit_code=1
		fi
	fi

	exit "${exit_code}"
}
trap 'cleanup "$?"' EXIT

git checkout -b "${TEST_BRANCH}"

# --- Step 1: Create a file that fails lint and verify the hook blocks the commit.
echo "Creating a Python file with a lint violation (unused import)."
cat >test_lint_fail.py <<'EOF'
import os  # noqa: F401 intentionally unused to trigger ruff
x=1
EOF
git add test_lint_fail.py

echo "Attempting to commit the lint-failing file — pre-commit hook must block it."
if git commit -m "test: lint-failing file (should be blocked)"; then
	echo "[FAIL] Commit should have been blocked by pre-commit hook." >&2
	exit 1
fi
echo "[OK] Commit correctly blocked by pre-commit hook."

# --- Step 2: Commit with --no-verify to bypass the hook.
echo "Committing the lint-failing file with --no-verify to bypass the hook."
git commit --no-verify -m "test: lint-failing file committed with --no-verify"
echo "[OK] Commit with --no-verify succeeded."

# --- Step 3: Revert the bypass commit.
echo "Reverting the --no-verify commit."
git revert --no-edit HEAD
echo "[OK] Revert succeeded."

# --- Step 4: Create a correct file and commit without --no-verify.
echo "Creating a clean Python file that passes lint."
cat >test_lint_pass.py <<'EOF'
def hello() -> None:
    print("hello")
EOF
git add test_lint_pass.py

echo "Committing the clean file without --no-verify — pre-commit hook must pass."
git commit -m "test: clean file committed via pre-commit hook"
echo "[OK] Commit without --no-verify succeeded."

echo "Returning to the original ref and deleting the temporary test branch."
git checkout "${ORIGINAL_REF}"
git branch -D "${TEST_BRANCH}"
trap - EXIT
cleanup 0
