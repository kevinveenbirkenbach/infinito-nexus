#!/usr/bin/env bash
set -euo pipefail

# Retag already built CI images (ci-<sha>) to <version> and latest (no rebuild).

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
echo "  CI_TAG     = ${CI_TAG}"
echo "  VERSION_TAG= ${VERSION_TAG}"
echo "  DISTROS    = ${DISTROS}"

for distro in ${DISTROS}; do
  src="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${distro}:${CI_TAG}"
  dst_ver="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${distro}:${VERSION_TAG}"
  dst_latest="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${distro}:latest"

  echo
  echo "==> ${distro}"
  echo "    source: ${src}"
  echo "    target: ${dst_ver}"
  echo "    target: ${dst_latest}"

  # Retag by digest (no rebuild)
  docker buildx imagetools create \
    -t "${dst_ver}" \
    -t "${dst_latest}" \
    "${src}"

  # Also publish alias tags for the default distro (arch): infinito:<tag>
  if [[ "${distro}" == "${DEFAULT_DISTRO}" ]]; then
    alias_ver="${REGISTRY}/${OWNER}/${REPO_PREFIX}:${VERSION_TAG}"
    alias_latest="${REGISTRY}/${OWNER}/${REPO_PREFIX}:latest"
    docker buildx imagetools create \
      -t "${alias_ver}" \
      -t "${alias_latest}" \
      "${src}"
  fi
done

echo
echo "Done retagging CI images."
