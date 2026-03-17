#!/usr/bin/env bash
set -euo pipefail

: "${MATRIX_DISTRO:?Missing MATRIX_DISTRO}"
: "${IMAGE_TAG:?Missing IMAGE_TAG}"
: "${GITHUB_REPOSITORY_OWNER:?Missing GITHUB_REPOSITORY_OWNER}"
ghcr_owner="$(echo "${GITHUB_REPOSITORY_OWNER}" | tr '[:upper:]' '[:lower:]')"

image="ghcr.io/${ghcr_owner}/infinito-${MATRIX_DISTRO}:${IMAGE_TAG}"
max_attempts="${MAX_WAIT_ATTEMPTS:-180}"
sleep_seconds="${WAIT_SLEEP_SECONDS:-10}"

echo "Fork pull_request detected; waiting for image built via pull_request_target:"
echo "  ${image}"

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
