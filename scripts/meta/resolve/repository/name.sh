#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${INFINITO_IMAGE_REPOSITORY:-}" ]]; then
  printf '%s\n' "${INFINITO_IMAGE_REPOSITORY,,}"
  exit 0
fi

if [[ -n "${REPO_PREFIX:-}" ]]; then
  printf '%s\n' "${REPO_PREFIX,,}"
  exit 0
fi

if [[ -n "${GITHUB_REPOSITORY:-}" ]]; then
  repo_name="${GITHUB_REPOSITORY#*/}"
  printf '%s\n' "${repo_name,,}"
  exit 0
fi

if git_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  repo_name="$(basename "${git_root}")"
  printf '%s\n' "${repo_name,,}"
  exit 0
fi

echo "ERROR: Could not resolve repository name from INFINITO_IMAGE_REPOSITORY, REPO_PREFIX, GITHUB_REPOSITORY or git metadata." >&2
exit 1
