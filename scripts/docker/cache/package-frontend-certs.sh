#!/usr/bin/env bash
# shellcheck shell=bash
#
# Host wrapper that runs the in-container cert generator
# (compose/package-cache-frontend/cert-gen.sh) inside a throw-away
# alpine container. The container approach lets the docker daemon
# create the bind-mount source paths under /var/cache/infinito/...
# without requiring the invoking shell to have write access to those
# host paths (sandboxed tooling, non-root operators, …).
#
# Pattern equivalent to scripts/docker/cache/registry-ca.sh except
# that this layer needs the certs to exist on the host BEFORE the
# package-cache-frontend nginx service starts (nginx fails on
# missing ssl_certificate files), so the generation is not done
# inside the frontend container itself.
#
# See docs/requirements/012-package-cache-nexus3-oss.md.

set -euo pipefail

: "${INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR:?Source scripts/meta/env/cache/package.sh first}"
: "${INFINITO_PACKAGE_CACHE_FRONTEND_CERTS_DIR:?Source scripts/meta/env/cache/package.sh first}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
INNER_SCRIPT="${REPO_ROOT}/compose/package-cache-frontend/cert-gen.sh"

if [[ ! -r "${INNER_SCRIPT}" ]]; then
	echo "[package-frontend-certs] missing inner script: ${INNER_SCRIPT}" >&2
	exit 1
fi

# Pin the alpine tag so re-runs are deterministic and the apk index
# the container fetches stays consistent across hosts.
ALPINE_IMAGE="${INFINITO_PACKAGE_CACHE_FRONTEND_INIT_IMAGE:-alpine:3.20}"

exec docker run --rm \
	-v "${INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR}:/ca" \
	-v "${INFINITO_PACKAGE_CACHE_FRONTEND_CERTS_DIR}:/certs" \
	-v "${INNER_SCRIPT}:/work/cert-gen.sh:ro" \
	--entrypoint /bin/sh \
	"${ALPINE_IMAGE}" \
	/work/cert-gen.sh
