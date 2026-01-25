#!/usr/bin/env bash
set -euo pipefail

# Retag already built CI images (ci-<sha>) to <version> and latest (no rebuild).
# Now also retags slim images: <repo>-<distro>-slim:* and alias <repo>-slim:*

OWNER="${OWNER:-${GITHUB_REPOSITORY_OWNER:-}}"
[[ -n "${OWNER}" ]] || { echo "ERROR: OWNER not set"; exit 2; }

REGISTRY="${REGISTRY:-ghcr.io}"
REPO_PREFIX="${REPO_PREFIX:-infinito}"
DISTROS="${DISTROS:-arch debian ubuntu fedora centos}"
DEFAULT_DISTRO="${DEFAULT_DISTRO:-arch}"

# VERSION_TAG must be like "v1.2.3"
VERSION_TAG="${VERSION_TAG:-${GITHUB_REF_NAME:-}}"
[[ -n "${VERSION_TAG}" ]] || { echo "ERROR: VERSION_TAG not set"; exit 2; }

# CI_TAG should be "ci-<sha>"
CI_TAG="${CI_TAG:-ci-${GITHUB_SHA:-}}"
[[ -n "${CI_TAG}" ]] || { echo "ERROR: CI_TAG not set"; exit 2; }

echo "Retagging CI images:"
echo "  CI_TAG      = ${CI_TAG}"
echo "  VERSION_TAG = ${VERSION_TAG}"
echo "  DISTROS     = ${DISTROS}"

retag_set() {
  local src="$1"
  local dst_ver="$2"
  local dst_latest="$3"

  echo "    source: ${src}"
  echo "    target: ${dst_ver}"
  echo "    target: ${dst_latest}"

  docker buildx imagetools create \
    -t "${dst_ver}" \
    -t "${dst_latest}" \
    "${src}"
}

for distro in ${DISTROS}; do
  echo
  echo "==> ${distro}"

  # FULL
  src="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${distro}:${CI_TAG}"
  dst_ver="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${distro}:${VERSION_TAG}"
  dst_latest="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${distro}:latest"
  retag_set "${src}" "${dst_ver}" "${dst_latest}"

  if [[ "${distro}" == "${DEFAULT_DISTRO}" ]]; then
    alias_ver="${REGISTRY}/${OWNER}/${REPO_PREFIX}:${VERSION_TAG}"
    alias_latest="${REGISTRY}/${OWNER}/${REPO_PREFIX}:latest"
    docker buildx imagetools create -t "${alias_ver}" -t "${alias_latest}" "${src}"
  fi

  # SLIM
  src_slim="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${distro}-slim:${CI_TAG}"
  dst_ver_slim="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${distro}-slim:${VERSION_TAG}"
  dst_latest_slim="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${distro}-slim:latest"
  retag_set "${src_slim}" "${dst_ver_slim}" "${dst_latest_slim}"

  if [[ "${distro}" == "${DEFAULT_DISTRO}" ]]; then
    alias_ver_slim="${REGISTRY}/${OWNER}/${REPO_PREFIX}-slim:${VERSION_TAG}"
    alias_latest_slim="${REGISTRY}/${OWNER}/${REPO_PREFIX}-slim:latest"
    docker buildx imagetools create -t "${alias_ver_slim}" -t "${alias_latest_slim}" "${src_slim}"
  fi
done

echo
echo "Done retagging CI images (full + slim)."
