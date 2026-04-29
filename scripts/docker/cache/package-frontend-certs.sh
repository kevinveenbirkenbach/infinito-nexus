#!/usr/bin/env bash
# shellcheck shell=bash
#
# Idempotent CA + per-hostname server-cert generator for the
# `package-cache-frontend` nginx service.
#
# The frontend terminates TLS for upstream hostnames (pypi.org,
# registry.npmjs.org, …) so that the runner can DNS-hijack those
# hostnames to the frontend and reverse-proxy them onto the Sonatype
# Nexus 3 OSS pull-through cache without rewriting any client URLs.
# For that to work, every TLS client inside the runner must trust
# certs signed by this CA.
#
# Pattern mirrors scripts/docker/cache/registry-ca.sh. Same idea, one
# layer up: registry-cache MITMs Docker image pulls; this CA backs
# package-manager pulls.
#
# Outputs (idempotent — no rewrite when valid >30d):
#   ${INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR}/ca.crt
#   ${INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR}/ca.key
#   ${INFINITO_PACKAGE_CACHE_FRONTEND_CERTS_DIR}/<hostname>.crt
#   ${INFINITO_PACKAGE_CACHE_FRONTEND_CERTS_DIR}/<hostname>.key
#
# See docs/requirements/012-package-cache-nexus3-oss.md.

set -euo pipefail

: "${INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR:?Source scripts/meta/env/cache/package.sh first}"
: "${INFINITO_PACKAGE_CACHE_FRONTEND_CERTS_DIR:?Source scripts/meta/env/cache/package.sh first}"

CA_DIR="${INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR}"
CERTS_DIR="${INFINITO_PACKAGE_CACHE_FRONTEND_CERTS_DIR}"
CA_CRT="${CA_DIR}/ca.crt"
CA_KEY="${CA_DIR}/ca.key"

# 10-year CA, 2-year leaf. Re-run after expiry rotates everything in
# place. Cache traffic is internal-only; CA private key never leaves
# the host.
CA_DAYS=3650
LEAF_DAYS=730

# Single source of truth for the upstream-hostname → server-cert list.
# Must stay in sync with the nginx server-blocks in
# compose/package-cache-frontend/upstreams.conf and with the
# extra_hosts emitted by cli/deploy/development/compose.py.
HOSTNAMES=(
	pypi.org
	files.pythonhosted.org
	registry.npmjs.org
	rubygems.org
	index.rubygems.org
	repo.packagist.org
	proxy.golang.org
	dl-cdn.alpinelinux.org
	raw.githubusercontent.com
	codeload.github.com
)

log() { printf '[package-frontend-certs] %s\n' "$*" >&2; }

mkdir -p "${CA_DIR}" "${CERTS_DIR}"
chmod 0700 "${CA_DIR}"

cert_still_valid() {
	# Returns 0 (true) if the cert exists and stays valid for >30 days.
	local crt="$1"
	[[ -s "${crt}" ]] || return 1
	openssl x509 -in "${crt}" -noout -checkend $((30 * 86400)) >/dev/null 2>&1
}

ensure_ca() {
	if cert_still_valid "${CA_CRT}" && [[ -s "${CA_KEY}" ]]; then
		log "CA already valid: ${CA_CRT}"
		return 0
	fi
	log "Generating new root CA at ${CA_CRT}"
	openssl genrsa -out "${CA_KEY}" 4096 >/dev/null 2>&1
	chmod 0600 "${CA_KEY}"
	openssl req -x509 -new -nodes \
		-key "${CA_KEY}" \
		-sha256 \
		-days "${CA_DAYS}" \
		-subj "/CN=Infinito Package-Cache Frontend CA/O=Infinito.Nexus" \
		-out "${CA_CRT}" >/dev/null 2>&1
	chmod 0644 "${CA_CRT}"
}

ensure_leaf() {
	local hostname="$1"
	local crt="${CERTS_DIR}/${hostname}.crt"
	local key="${CERTS_DIR}/${hostname}.key"

	if cert_still_valid "${crt}" && [[ -s "${key}" ]]; then
		# Also confirm the existing leaf was signed by the current CA.
		# A stale leaf signed by an older CA would break TLS validation
		# even though it has not expired.
		if openssl verify -CAfile "${CA_CRT}" "${crt}" >/dev/null 2>&1; then
			return 0
		fi
		log "Leaf for ${hostname} no longer chains to current CA; regenerating"
	fi

	log "Generating leaf cert for ${hostname}"
	openssl genrsa -out "${key}" 2048 >/dev/null 2>&1
	chmod 0600 "${key}"

	# OpenSSL extfile carrying SAN + serverAuth EKU. Modern TLS clients
	# (pip's urllib3, npm, curl≥7.66) ignore the deprecated CN-as-host
	# fallback, so the SAN entry is mandatory.
	local extfile
	extfile="$(mktemp)"
	cat >"${extfile}" <<-EOF
		subjectAltName = DNS:${hostname}
		extendedKeyUsage = serverAuth
	EOF

	local csr
	csr="$(mktemp)"
	openssl req -new \
		-key "${key}" \
		-subj "/CN=${hostname}" \
		-out "${csr}" >/dev/null 2>&1

	openssl x509 -req \
		-in "${csr}" \
		-CA "${CA_CRT}" \
		-CAkey "${CA_KEY}" \
		-CAcreateserial \
		-out "${crt}" \
		-days "${LEAF_DAYS}" \
		-sha256 \
		-extfile "${extfile}" >/dev/null 2>&1
	chmod 0644 "${crt}"

	rm -f "${csr}" "${extfile}"
}

ensure_ca
for h in "${HOSTNAMES[@]}"; do
	ensure_leaf "${h}"
done
log "CA + ${#HOSTNAMES[@]} leaf certs ready under ${CERTS_DIR}"
