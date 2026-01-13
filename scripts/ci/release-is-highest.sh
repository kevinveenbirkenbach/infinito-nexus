#!/usr/bin/env bash
set -euo pipefail

# Determine whether the current tag is the highest v* tag.
# Outputs: is_highest=true|false to $GITHUB_OUTPUT.

: "${GITHUB_REF:?GITHUB_REF is required}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"

version_tag="${GITHUB_REF#refs/tags/}" # e.g. v1.2.3
echo "Current version tag: ${version_tag}"

all_v_tags="$(git tag --list 'v*' || true)"
if [[ -z "${all_v_tags}" ]]; then
  echo "No version tags found."
  echo "is_highest=false" >> "$GITHUB_OUTPUT"
  exit 0
fi

latest_tag="$(printf '%s\n' "${all_v_tags}" | sort -V | tail -n1)"
echo "Highest version tag: ${latest_tag}"

if [[ "${version_tag}" == "${latest_tag}" ]]; then
  echo "is_highest=true" >> "$GITHUB_OUTPUT"
else
  echo "is_highest=false" >> "$GITHUB_OUTPUT"
fi
