#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${OWNER:-}" ]]; then
  printf '%s\n' "${OWNER,,}"
  exit 0
fi

if [[ -n "${GITHUB_REPOSITORY_OWNER:-}" ]]; then
  printf '%s\n' "${GITHUB_REPOSITORY_OWNER,,}"
  exit 0
fi

if [[ -n "${GITHUB_REPOSITORY:-}" ]]; then
  owner="${GITHUB_REPOSITORY%%/*}"
  printf '%s\n' "${owner,,}"
  exit 0
fi

if remote_url="$(git config --get remote.origin.url 2>/dev/null)" && [[ -n "${remote_url}" ]]; then
  remote_path="${remote_url%.git}"

  if [[ "${remote_path}" == *://* ]]; then
    remote_path="${remote_path#*://}"
    remote_path="${remote_path#*@}"
    remote_path="${remote_path#*/}"
  elif [[ "${remote_path}" == *:* ]]; then
    remote_path="${remote_path#*:}"
  fi

  if [[ "${remote_path}" == */* ]]; then
    owner="${remote_path%%/*}"
    printf '%s\n' "${owner,,}"
    exit 0
  fi
fi

echo "ERROR: Could not resolve repository owner from OWNER, GITHUB_REPOSITORY_OWNER, GITHUB_REPOSITORY or git remote." >&2
exit 1
