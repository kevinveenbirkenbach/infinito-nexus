#!/usr/bin/env bash
set -euo pipefail

# Publish all distro images (full + virgin) to a registry via image.sh --publish
#
# Required env:
#   OWNER      (e.g. GITHUB_REPOSITORY_OWNER)
#   VERSION    (e.g. 1.2.3)
#
# Optional env:
#   REGISTRY   (default: ghcr.io)
#   IS_STABLE  (default: false)
#   DISTROS    (default: "arch debian ubuntu fedora centos")

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

REGISTRY="${REGISTRY:-ghcr.io}"
IS_STABLE="${IS_STABLE:-false}"
DISTROS="${DISTROS:-arch debian ubuntu fedora centos}"

: "${OWNER:?Environment variable OWNER must be set (e.g. github.repository_owner)}"
: "${VERSION:?Environment variable VERSION must be set (e.g. 1.2.3)}"

echo "[publish] REGISTRY=${REGISTRY}"
echo "[publish] OWNER=${OWNER}"
echo "[publish] VERSION=${VERSION}"
echo "[publish] IS_STABLE=${IS_STABLE}"
echo "[publish] DISTROS=${DISTROS}"

for d in ${DISTROS}; do
	echo
	echo "============================================================"
	echo "[publish] INFINITO_DISTRO=${d}"
	echo "============================================================"

	# virgin
	INFINITO_DISTRO="${d}" bash "${SCRIPT_DIR}/image.sh" \
		--publish \
		--registry "${REGISTRY}" \
		--owner "${OWNER}" \
		--version "${VERSION}" \
		--stable "${IS_STABLE}" \
		--target virgin

	# full (default target)
	INFINITO_DISTRO="${d}" bash "${SCRIPT_DIR}/image.sh" \
		--publish \
		--registry "${REGISTRY}" \
		--owner "${OWNER}" \
		--version "${VERSION}" \
		--stable "${IS_STABLE}"
done

echo
echo "[publish] Done."
