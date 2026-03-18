#!/usr/bin/env bash
set -euo pipefail

: "${MATRIX_DISTRO:?Missing MATRIX_DISTRO}"
: "${IMAGE_TAG:?Missing IMAGE_TAG}"
: "${GITHUB_REPOSITORY_OWNER:?Missing GITHUB_REPOSITORY_OWNER}"
: "${IMAGE_WAIT_SLEEP_SECONDS:?Missing IMAGE_WAIT_SLEEP_SECONDS}"
: "${IMAGE_WAIT_ATTEMPTS:?Missing IMAGE_WAIT_ATTEMPTS}"

image="ghcr.io/${GITHUB_REPOSITORY_OWNER}/infinito-${MATRIX_DISTRO}:${IMAGE_TAG}"
sleep_seconds="${IMAGE_WAIT_SLEEP_SECONDS}"
max_attempts="${IMAGE_WAIT_ATTEMPTS}"
pr_number="${PR_NUMBER:-}"

echo "Fork pull_request detected; waiting for image built via pull_request_target:"
echo "  ${image}"

if [[ -n "${pr_number}" && -n "${GITHUB_REPOSITORY:-}" ]]; then
	ref="refs/pull/${pr_number}/merge"
	repo_url="https://github.com/${GITHUB_REPOSITORY}.git"
	current_sha="$(git ls-remote "${repo_url}" "${ref}" | awk 'NR==1 {print $1}')"
	if [[ "${current_sha}" =~ ^[0-9a-f]{40}$ ]]; then
		current_tag="ci-${current_sha}"
		if [[ "${current_tag}" != "${IMAGE_TAG}" ]]; then
			echo "This pull_request run is stale: expected ${IMAGE_TAG}, but current ${ref} resolves to ${current_tag}." >&2
			echo "Re-run the latest pull_request workflow for this PR instead of re-running an older run." >&2
			exit 1
		fi
	fi
fi

for attempt in $(seq 1 "${max_attempts}"); do
	if docker buildx imagetools inspect "${image}" >/dev/null 2>&1; then
		echo "Image is available: ${image}"
		exit 0
	fi
	echo "[${attempt}/${max_attempts}] Waiting for image..."
	sleep "${sleep_seconds}"
done

echo "Timed out waiting for prebuilt image: ${image}" >&2
exit 1
