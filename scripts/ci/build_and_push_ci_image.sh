#!/usr/bin/env bash
set -euo pipefail

: "${BUILD_CONTEXT_DIR:?Missing BUILD_CONTEXT_DIR}"
: "${MATRIX_DISTRO:?Missing MATRIX_DISTRO}"
: "${IMAGE_TAG:?Missing IMAGE_TAG}"
: "${GITHUB_REPOSITORY_OWNER:?Missing GITHUB_REPOSITORY_OWNER}"
: "${USE_NIX_TOKEN:?Missing USE_NIX_TOKEN}"
ghcr_owner="$(echo "${GITHUB_REPOSITORY_OWNER}" | tr '[:upper:]' '[:lower:]')"

max_attempts="${MAX_ATTEMPTS:-7}"
retry_delay_seconds="${RETRY_DELAY_SECONDS:-20}"
attempt=1

nix_arg=()
if [[ "${USE_NIX_TOKEN}" == "true" ]]; then
  : "${NIX_GITHUB_TOKEN:?Missing NIX_GITHUB_TOKEN}"
  nix_arg=( --build-arg "NIX_CONFIG=access-tokens = github.com=${NIX_GITHUB_TOKEN}" )
else
  echo "pull_request_target on fork detected: skipping NIX_CONFIG token build-arg."
fi

while true; do
  echo "=== Build & push attempt ${attempt}/${max_attempts} ==="

  if docker buildx build \
    --file "${BUILD_CONTEXT_DIR}/Dockerfile" \
    --push \
    --tag "ghcr.io/${ghcr_owner}/infinito-${MATRIX_DISTRO}:${IMAGE_TAG}" \
    --build-arg "PKGMGR_IMAGE=ghcr.io/kevinveenbirkenbach/pkgmgr-${MATRIX_DISTRO}:stable" \
    "${nix_arg[@]}" \
    --cache-from "type=gha,scope=infinito-${MATRIX_DISTRO}" \
    --cache-to "type=gha,mode=max,scope=infinito-${MATRIX_DISTRO}" \
    "${BUILD_CONTEXT_DIR}"; then
    echo "Build & push succeeded on attempt ${attempt}/${max_attempts}."
    break
  fi

  if [[ "${attempt}" -ge "${max_attempts}" ]]; then
    echo "Build & push failed after ${max_attempts} attempts."
    exit 1
  fi

  echo "Attempt ${attempt} failed. Retrying in ${retry_delay_seconds}s..."
  sleep "${retry_delay_seconds}"
  attempt=$((attempt + 1))
done
