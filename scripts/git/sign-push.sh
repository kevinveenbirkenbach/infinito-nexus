#!/usr/bin/env bash
# Sign every unpushed commit on the current branch with the operator's GPG key
# and push. Intended to replace direct `git push` from inside the Claude sandbox.
#
# Must run OUTSIDE the sandbox so gpg-agent/pinentry can reach ~/.gnupg.
set -euo pipefail

if [[ -n "${CLAUDE_CODE:-}${CLAUDECODE:-}" ]]; then
	echo "ERROR: sign-push must run outside the Claude sandbox." >&2
	exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
	echo "ERROR: uncommitted changes present. Commit or stash before signing." >&2
	exit 1
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "${BRANCH}" == "HEAD" ]]; then
	echo "ERROR: detached HEAD." >&2
	exit 1
fi

git fetch --quiet origin

PUSH_NEEDS_UPSTREAM=0
BASE=""
if UPSTREAM="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"; then
	BASE="$(git merge-base HEAD "${UPSTREAM}")"
else
	PUSH_NEEDS_UPSTREAM=1
	for CAND in origin/main origin/master; do
		if git rev-parse --verify --quiet "${CAND}" >/dev/null; then
			BASE="$(git merge-base HEAD "${CAND}")"
			break
		fi
	done
fi

if [[ -z "${BASE}" ]]; then
	echo "ERROR: could not determine base commit (no upstream, no origin/main|master)." >&2
	exit 1
fi

COUNT="$(git rev-list --count "${BASE}..HEAD")"
if [[ "${COUNT}" -eq 0 ]]; then
	echo "Nothing to sign or push."
	exit 0
fi

UNSIGNED="$(git log --format='%G?' "${BASE}..HEAD" | grep -cvE '^G$' || true)"

if [[ "${UNSIGNED}" -gt 0 ]]; then
	echo "Signing ${UNSIGNED} of ${COUNT} commit(s) in ${BASE}..HEAD"
	GIT_SEQUENCE_EDITOR=: git rebase --rebase-merges \
		--exec 'git commit --amend --allow-empty --no-edit -S' "${BASE}"
else
	echo "All ${COUNT} commit(s) already GPG-signed; skipping re-sign."
fi

if [[ "${PUSH_NEEDS_UPSTREAM}" -eq 1 ]]; then
	git push -u origin "${BRANCH}"
else
	git push --force-with-lease
fi
