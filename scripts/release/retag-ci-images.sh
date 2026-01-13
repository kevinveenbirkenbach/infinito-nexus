#!/usr/bin/env bash
set -euo pipefail

# Retag already built CI images (ci-<sha>) to <version> and latest (no rebuild).
#
# Required env:
#   OWNER        (e.g. github.repository_owner)
#   VERSION      (e.g. 1.2.3)  OR  GITHUB_REF_NAME=v1.2.3
#   GITHUB_SHA
#
# Optional env:
#   REGISTRY        (default: ghcr.io)
#   REPO_PREFIX     (default: infinito)
#   DISTROS         (default: "arch debian ubuntu fedora centos")
#   DEFAULT_DISTRO  (default: arch)

: "${OWNER:?OWNER is required}"
: "${GITHUB_SHA:?GITHUB_SHA is required}"

REGISTRY="${REGISTRY:-ghcr.io}"
REPO_PREFIX="${REPO_PREFIX:-infinito}"
DISTROS="${DISTROS:-arch debian ubuntu fedora centos}"
DEFAULT_DISTRO="${DEFAULT_DISTRO:-arch}"

# VERSION can be provided directly or derived from GitHub tag name
if [[ -z "${VERSION:-}" ]]; then
  : "${GITHUB_REF_NAME:?Either VERSION or GITHUB_REF_NAME must be set}"
  VERSION="${GITHUB_REF_NAME#v}"
fi

CI_TAG="ci-${GITHUB_SHA}"

echo "[release] OWNER=${OWNER}"
echo "[release] VERSION=${VERSION}"
echo "[release] CI_TAG=${CI_TAG}"
echo "[release] DISTROS=${DISTROS}"
echo "[release] DEFAULT_DISTRO=${DEFAULT_DISTRO}"

retag_one() {
  local src="$1"
  local dst="$2"
  echo "[release] ${src} -> ${dst}"
  docker buildx imagetools create -t "${dst}" "${src}"
}

for d in ${DISTROS}; do
  base="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${d}"

  # full image: ci-<sha> -> version + latest
  retag_one "${base}:${CI_TAG}" "${base}:${VERSION}"
  retag_one "${base}:${CI_TAG}" "${base}:latest"

  # aliases for default distro (arch): infinito -> version + latest
  if [[ "${d}" == "${DEFAULT_DISTRO}" ]]; then
    alias_base="${REGISTRY}/${OWNER}/${REPO_PREFIX}"
    retag_one "${base}:${CI_TAG}" "${alias_base}:${VERSION}"
    retag_one "${base}:${CI_TAG}" "${alias_base}:latest"
  fi
done
