#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_OUTPUT:?Missing GITHUB_OUTPUT}"
: "${VERSION_TAG:?Missing VERSION_TAG}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repository_dir="${REPOSITORY_DIR:-.}"

highest_tag="$(
	REPOSITORY_DIR="${repository_dir}" \
		"${script_dir}/highest_version_tag.sh"
)"

publish_latest="false"
if [[ -n "${highest_tag}" && "${VERSION_TAG}" == "${highest_tag}" ]]; then
	publish_latest="true"
fi

{
	echo "publish_latest=${publish_latest}"
} >>"${GITHUB_OUTPUT}"

echo "Resolved highest version tag: ${highest_tag:-<none>}"
echo "Release tag ${VERSION_TAG} updates latest: ${publish_latest}"
