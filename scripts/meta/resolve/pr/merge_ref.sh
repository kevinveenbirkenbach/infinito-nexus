#!/usr/bin/env bash
set -euo pipefail

: "${PR_NUMBER:?Missing PR_NUMBER}"
: "${GITHUB_REPOSITORY:?Missing GITHUB_REPOSITORY}"
: "${GITHUB_OUTPUT:?Missing GITHUB_OUTPUT}"

ref="refs/pull/${PR_NUMBER}/merge"
repo_url="https://github.com/${GITHUB_REPOSITORY}.git"
payload_sha="${PR_MERGE_SHA:-}"
remote_sha="$(git ls-remote "${repo_url}" "${ref}" | awk 'NR==1 {print $1}')"
sha=""

if [[ -n "${payload_sha}" && ! "${payload_sha}" =~ ^[0-9a-f]{40}$ ]]; then
	echo "Invalid PR_MERGE_SHA '${payload_sha}', ignoring event payload." >&2
	payload_sha=""
fi

if [[ -n "${remote_sha}" && ! "${remote_sha}" =~ ^[0-9a-f]{40}$ ]]; then
	echo "Invalid remote merge SHA '${remote_sha}' for ${ref}, ignoring live ref." >&2
	remote_sha=""
fi

if [[ -n "${remote_sha}" ]]; then
	sha="${remote_sha}"
	if [[ -n "${payload_sha}" && "${payload_sha}" != "${remote_sha}" ]]; then
		echo "Event merge SHA ${payload_sha} differs from live ${ref} (${remote_sha}); using live ref." >&2
	fi
elif [[ -n "${payload_sha}" ]]; then
	sha="${payload_sha}"
	echo "Falling back to event merge SHA ${payload_sha} because ${ref} could not be resolved live." >&2
else
	echo "Failed to resolve merge SHA for ${ref}" >&2
	exit 1
fi

checkout_ref="${sha}"

{
	echo "checkout_ref=${checkout_ref}"
	echo "image_tag=ci-${sha}"
} >>"${GITHUB_OUTPUT}"

echo "Resolved fork PR merge ref ${ref} -> ${sha} (checkout_ref=${checkout_ref})"
