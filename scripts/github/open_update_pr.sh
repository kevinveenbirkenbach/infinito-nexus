#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?Missing GH_TOKEN}"
: "${UPDATE_BRANCH_PREFIX:?Missing UPDATE_BRANCH_PREFIX}"
: "${UPDATE_COMMIT_MESSAGE:?Missing UPDATE_COMMIT_MESSAGE}"
: "${UPDATE_PR_TITLE:?Missing UPDATE_PR_TITLE}"
: "${UPDATE_PR_BODY:?Missing UPDATE_PR_BODY}"

UPDATE_BASE_BRANCH="${UPDATE_BASE_BRANCH:-master}"
UPDATE_BRANCH_SUFFIX="${UPDATE_BRANCH_SUFFIX:-$(date +%Y%m%d)}"
BRANCH="${UPDATE_BRANCH_PREFIX}-${UPDATE_BRANCH_SUFFIX}"

if ! command -v gh >/dev/null 2>&1; then
	echo "ERROR: gh CLI not found." >&2
	exit 1
fi

REPO="$(git remote get-url origin | sed 's|.*github\.com[:/]||' | sed 's|\.git$||')"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
git checkout -B "${BRANCH}"

if (($# > 0)); then
	git add -- "$@"
else
	git add -A
fi

if git diff --cached --quiet; then
	echo "No staged update changes found."
	exit 0
fi

git commit -m "${UPDATE_COMMIT_MESSAGE}"
git push --force origin "${BRANCH}"

PR_NUMBER="$(
	gh pr list \
		--repo "${REPO}" \
		--head "${BRANCH}" \
		--base "${UPDATE_BASE_BRANCH}" \
		--json number \
		--jq '.[0].number // empty'
)"

if [[ -n "${PR_NUMBER}" ]]; then
	echo "Updating existing PR #${PR_NUMBER} for ${BRANCH}"
	gh pr edit "${PR_NUMBER}" \
		--repo "${REPO}" \
		--title "${UPDATE_PR_TITLE}" \
		--body "${UPDATE_PR_BODY}"
else
	echo "Creating PR for ${BRANCH}"
	gh pr create \
		--repo "${REPO}" \
		--title "${UPDATE_PR_TITLE}" \
		--body "${UPDATE_PR_BODY}" \
		--base "${UPDATE_BASE_BRANCH}" \
		--head "${BRANCH}"
fi
