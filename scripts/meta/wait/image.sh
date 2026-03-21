#!/usr/bin/env bash
set -euo pipefail

: "${MATRIX_DISTRO:?Missing MATRIX_DISTRO}"
: "${IMAGE_TAG:?Missing IMAGE_TAG}"
: "${IMAGE_WAIT_SLEEP_SECONDS:?Missing IMAGE_WAIT_SLEEP_SECONDS}"
: "${IMAGE_WAIT_ATTEMPTS:?Missing IMAGE_WAIT_ATTEMPTS}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ghcr_owner="$(scripts/meta/resolve/repository/owner.sh)"
repo_name="${IMAGE_REPO_NAME:-$("${script_dir}/../resolve/repository/name.sh")}"

image="ghcr.io/${ghcr_owner}/${repo_name}/${MATRIX_DISTRO}:${IMAGE_TAG}"
sleep_seconds="${IMAGE_WAIT_SLEEP_SECONDS}"
max_attempts="${IMAGE_WAIT_ATTEMPTS}"
pr_number="${PR_NUMBER:-}"
last_error=""

normalize_error() {
	local raw="${1:-}"
	raw="${raw//$'\r'/ }"
	raw="${raw//$'\n'/ }"
	raw="$(printf '%s' "${raw}" | sed -E 's/[[:space:]]+/ /g; s/^ //; s/ $//')"
	if [[ -z "${raw}" ]]; then
		raw="inspect command exited non-zero without stderr output"
	fi
	printf '%s\n' "${raw}"
}

classify_error() {
	local message="${1,,}"

	if [[ "${message}" == *"unauthorized"* ]] || [[ "${message}" == *"authentication required"* ]] || [[ "${message}" == *"insufficient_scope"* ]] || [[ "${message}" == *"access denied"* ]] || [[ "${message}" == *"requested access to the resource is denied"* ]] || [[ "${message}" == *"forbidden"* ]]; then
		printf '%s\n' "registry auth/permission error"
		return
	fi

	if [[ "${message}" == *"not found"* ]] || [[ "${message}" == *"manifest unknown"* ]] || [[ "${message}" == *"no such manifest"* ]] || [[ "${message}" == *"name unknown"* ]]; then
		printf '%s\n' "image tag not published yet"
		return
	fi

	if [[ "${message}" == *"timeout"* ]] || [[ "${message}" == *"tls handshake timeout"* ]] || [[ "${message}" == *"temporary failure"* ]] || [[ "${message}" == *"connection refused"* ]] || [[ "${message}" == *"connection reset"* ]] || [[ "${message}" == *"i/o timeout"* ]] || [[ "${message}" == *"no such host"* ]]; then
		printf '%s\n' "registry/network error"
		return
	fi

	printf '%s\n' "unexpected inspect error"
}

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
	inspect_output=""
	if inspect_output="$(docker buildx imagetools inspect "${image}" 2>&1)"; then
		echo "Image is available: ${image}"
		exit 0
	fi

	normalized_error="$(normalize_error "${inspect_output}")"
	error_kind="$(classify_error "${normalized_error}")"

	if [[ "${normalized_error}" != "${last_error}" ]]; then
		echo "[${attempt}/${max_attempts}] Waiting for image... reason: ${error_kind}"
		echo "Inspect error: ${normalized_error}"
		last_error="${normalized_error}"
	else
		echo "[${attempt}/${max_attempts}] Waiting for image... reason: ${error_kind}"
	fi

	if [[ "${error_kind}" == "registry auth/permission error" ]]; then
		echo "Prebuilt image cannot be inspected because GHCR denied access." >&2
		echo "Image: ${image}" >&2
		echo "Inspect error: ${normalized_error}" >&2
		exit 1
	fi

	sleep "${sleep_seconds}"
done

echo "Timed out waiting for prebuilt image: ${image}" >&2
if [[ -n "${last_error}" ]]; then
	echo "Last inspect error: ${last_error}" >&2
fi
exit 1
