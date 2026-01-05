#!/usr/bin/env bash
set -euo pipefail

# Retag already published VERSION images to :stable
# - does NOT rebuild
# - does NOT touch :latest
#
# Required env:
#   OWNER      (e.g. github.repository_owner)
#   VERSION    (e.g. 1.2.3)
#
# Optional env:
#   REGISTRY       (default: ghcr.io)
#   DISTROS        (default: "arch debian ubuntu fedora centos")
#   REPO_PREFIX    (default: infinito)
#   DEFAULT_DISTRO (default: arch)

REGISTRY="${REGISTRY:-ghcr.io}"
DISTROS="${DISTROS:-arch debian ubuntu fedora centos}"
REPO_PREFIX="${REPO_PREFIX:-infinito}"
DEFAULT_DISTRO="${DEFAULT_DISTRO:-arch}"

: "${OWNER:?Environment variable OWNER must be set (e.g. github.repository_owner)}"
: "${VERSION:?Environment variable VERSION must be set (e.g. 1.2.3)}"

echo "[retag-stable] REGISTRY=${REGISTRY}"
echo "[retag-stable] OWNER=${OWNER}"
echo "[retag-stable] VERSION=${VERSION}"
echo "[retag-stable] DISTROS=${DISTROS}"
echo "[retag-stable] REPO_PREFIX=${REPO_PREFIX}"
echo "[retag-stable] DEFAULT_DISTRO=${DEFAULT_DISTRO}"

retag_one() {
  local src="$1" # e.g. ghcr.io/owner/infinito-arch:1.2.3
  local dst="$2" # e.g. ghcr.io/owner/infinito-arch:stable

  echo "[retag-stable] ${src} -> ${dst}"
  docker buildx imagetools create -t "${dst}" "${src}"
}

for d in ${DISTROS}; do
  # full
  base="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${d}"
  retag_one "${base}:${VERSION}" "${base}:stable"

  # virgin
  base_v="${REGISTRY}/${OWNER}/${REPO_PREFIX}-${d}-virgin"
  retag_one "${base_v}:${VERSION}" "${base_v}:stable"

  # aliases for default distro
  if [[ "${d}" == "${DEFAULT_DISTRO}" ]]; then
    alias_base="${REGISTRY}/${OWNER}/${REPO_PREFIX}"
    retag_one "${alias_base}:${VERSION}" "${alias_base}:stable"

    alias_v="${REGISTRY}/${OWNER}/${REPO_PREFIX}-virgin"
    retag_one "${alias_v}:${VERSION}" "${alias_v}:stable"
  fi
done

echo "[retag-stable] Done."
