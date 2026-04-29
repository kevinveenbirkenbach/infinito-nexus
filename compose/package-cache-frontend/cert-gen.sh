#!/bin/sh
# Idempotent CA + per-hostname server-cert generator for the
# package-cache-frontend nginx service.
#
# Runs INSIDE a throw-away alpine container (driven by
# scripts/docker/cache/package-frontend-certs.sh) so that the host
# does not need write access to /var/cache/infinito/...; the docker
# daemon creates the bind-mount source paths and writes happen as
# root inside the container. Compare with registry-cache, which has
# rpardini/docker-registry-proxy generate its CA in-container too.
#
# Bind-mount layout the wrapper sets up:
#   /ca      -> ${INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR}    (rw)
#   /certs   -> ${INFINITO_PACKAGE_CACHE_FRONTEND_CERTS_DIR} (rw)
#
# Outputs (idempotent — no rewrite when valid >30d):
#   /ca/ca.crt
#   /ca/ca.key
#   /certs/<hostname>.crt
#   /certs/<hostname>.key

set -eu

CA_CRT=/ca/ca.crt
CA_KEY=/ca/ca.key

# 10-year CA, 2-year leaf. Re-run after expiry rotates everything in
# place. Cache traffic is internal-only; CA private key never leaves
# the host.
CA_DAYS=3650
LEAF_DAYS=730

# Single source of truth for the upstream-hostname → server-cert list.
# Must stay in sync with the nginx server-blocks in
# compose/package-cache-frontend/upstreams.conf and with the
# extra_hosts emitted by compose/cache.override.yml.
HOSTNAMES="pypi.org files.pythonhosted.org registry.npmjs.org rubygems.org index.rubygems.org repo.packagist.org proxy.golang.org dl-cdn.alpinelinux.org raw.githubusercontent.com codeload.github.com"

log() { printf '[package-frontend-certs] %s\n' "$*" >&2; }

ensure_openssl() {
	if command -v openssl >/dev/null 2>&1; then
		return 0
	fi
	log "openssl not present in image — installing via apk"
	# `--no-cache` keeps the apk index out of the layer; the index
	# fetch hits dl-cdn.alpinelinux.org. Once the package-cache is
	# itself transparent (DNS-hijack on the runner) this hop also
	# benefits, but the init container does not have the hijack —
	# an upstream apk fetch on first run is acceptable.
	apk add --no-cache openssl >/dev/null 2>&1
}

mkdir -p /ca /certs
chmod 0700 /ca

ensure_openssl

cert_still_valid() {
	# Returns 0 (true) if the cert exists and stays valid for >30 days.
	crt="$1"
	[ -s "${crt}" ] || return 1
	openssl x509 -in "${crt}" -noout -checkend 2592000 >/dev/null 2>&1
}

ensure_ca() {
	if cert_still_valid "${CA_CRT}" && [ -s "${CA_KEY}" ]; then
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
	hostname="$1"
	crt="/certs/${hostname}.crt"
	key="/certs/${hostname}.key"

	if cert_still_valid "${crt}" && [ -s "${key}" ]; then
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
	extfile="$(mktemp)"
	{
		printf 'subjectAltName = DNS:%s\n' "${hostname}"
		printf 'extendedKeyUsage = serverAuth\n'
	} >"${extfile}"

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
count=0
for h in ${HOSTNAMES}; do
	ensure_leaf "${h}"
	count=$((count + 1))
done
log "CA + ${count} leaf certs ready under /certs"
