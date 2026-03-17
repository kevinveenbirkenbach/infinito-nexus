#!/usr/bin/env bash
set -euo pipefail

: "${PR_NUMBER:?Missing PR_NUMBER}"
: "${GITHUB_REPOSITORY:?Missing GITHUB_REPOSITORY}"
: "${GITHUB_OUTPUT:?Missing GITHUB_OUTPUT}"

ref="refs/pull/${PR_NUMBER}/merge"
repo_url="https://github.com/${GITHUB_REPOSITORY}.git"
sha="${PR_MERGE_SHA:-}"
checkout_ref="${ref}"

if [[ -n "${sha}" ]]; then
  if [[ ! "${sha}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Invalid PR_MERGE_SHA '${sha}', falling back to ${ref}" >&2
    sha=""
  else
    checkout_ref="${sha}"
  fi
fi

if [[ -z "${sha}" ]]; then
  sha="$(git ls-remote "${repo_url}" "${ref}" | awk '{print $1}')"
  if [[ -z "${sha}" ]]; then
    echo "Failed to resolve merge SHA for ${ref}" >&2
    exit 1
  fi
  checkout_ref="${sha}"
fi

{
  echo "checkout_ref=${checkout_ref}"
  echo "image_tag=ci-${sha}"
} >> "${GITHUB_OUTPUT}"

echo "Resolved fork PR merge ref ${ref} -> ${sha} (checkout_ref=${checkout_ref})"
