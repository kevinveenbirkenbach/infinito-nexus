#!/usr/bin/env bash
# Install the package-cache-frontend CA into the runner's system trust
# store before any package manager (apt, pip, npm, gem, composer, …)
# makes outbound HTTPS calls.
#
# Pattern mirrors registry-cache-ca.sh. Difference in scope:
#   * registry-cache-ca.sh: trust store consumed by inner dockerd
#     (image pulls).
#   * package-frontend-ca.sh: trust store consumed by the runner's
#     own OS clients (apt-get/pip/curl/etc.) so they accept TLS
#     against the package-cache-frontend's per-hostname certs.
#
# Idempotent: safe to run on every boot.
set -eu

CA_SRC="/opt/package-frontend-ca.crt"

if command -v update-ca-certificates >/dev/null 2>&1; then
	CA_DST="/usr/local/share/ca-certificates/infinito-package-frontend.crt"
	CA_REBUILD=(update-ca-certificates)
elif command -v update-ca-trust >/dev/null 2>&1; then
	CA_DST="/etc/ca-certificates/trust-source/anchors/infinito-package-frontend.crt"
	CA_REBUILD=(update-ca-trust extract)
else
	echo "[package-frontend-ca] no supported CA trust tool" >&2
	exit 1
fi

# Bind-mount source defaults to /dev/null when the cache profile is
# inactive. An empty CA_SRC means: cache disabled, nothing to install.
# Exit cleanly so the runner deploys identically with the cache off.
if [ ! -s "${CA_SRC}" ]; then
	echo "[package-frontend-ca] ${CA_SRC} empty/absent; cache profile inactive; skipping" >&2
	exit 0
fi

if cmp -s "${CA_SRC}" "${CA_DST}" 2>/dev/null; then
	exit 0
fi

install -d -m 0755 "$(dirname "${CA_DST}")"
install -m 0644 "${CA_SRC}" "${CA_DST}"
"${CA_REBUILD[@]}" >/dev/null 2>&1
echo "[package-frontend-ca] installed ${CA_DST}" >&2
