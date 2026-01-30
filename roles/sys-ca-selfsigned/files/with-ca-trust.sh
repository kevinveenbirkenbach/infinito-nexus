#!/usr/bin/env sh
set -eu

: "${CA_TRUST_CERT:?CA_TRUST_CERT env var must be set (path to CA cert)}"
: "${CA_TRUST_NAME:?CA_TRUST_NAME env var must be set (trust anchor name)}"

VERBOSE="${VERBOSE:-1}"

log() {
  if [ "$VERBOSE" = "1" ]; then
    echo "[with-ca-trust] $*" >&2
  fi
}

run() {
  log "RUN: $*"
  "$@"
}

log "Starting CA trust installation"
log "CA_TRUST_CERT=$CA_TRUST_CERT"
log "CA_TRUST_NAME=$CA_TRUST_NAME"

if [ ! -r "$CA_TRUST_CERT" ]; then
  echo "[with-ca-trust] ERROR: CA certificate not readable: $CA_TRUST_CERT" >&2
  exit 2
fi

# Sanitize trust name
name="$(printf '%s' "$CA_TRUST_NAME" | tr -c 'A-Za-z0-9._-' '_' )"
if [ -z "$name" ]; then
  echo "[with-ca-trust] ERROR: CA_TRUST_NAME resolved to empty after sanitization" >&2
  exit 4
fi

log "Sanitized trust name: $name"

installed=0

# Always provide env-based trust hints as a fallback (works for many TLS stacks)
export SSL_CERT_FILE="$CA_TRUST_CERT"
export REQUESTS_CA_BUNDLE="$CA_TRUST_CERT"
export CURL_CA_BUNDLE="$CA_TRUST_CERT"
# Optional (harmless if unused; helps Node-based tools if any)
export NODE_EXTRA_CA_CERTS="$CA_TRUST_CERT"

install_anchor() {
  src="$1"
  dst="$2"

  log "Installing CA anchor: $dst"
  if run mkdir -p "$(dirname "$dst")" 2>/dev/null && run cp -f "$src" "$dst" 2>/dev/null; then
    installed=1
    return 0
  fi

  log "WARN: Cannot write CA anchor to $dst (no permission). Falling back to SSL_CERT_FILE/REQUESTS_CA_BUNDLE only."
  return 1
}

#
# Debian / Ubuntu style
#
if command -v update-ca-certificates >/dev/null 2>&1; then
  log "Detected update-ca-certificates"
  if install_anchor "$CA_TRUST_CERT" "/usr/local/share/ca-certificates/${name}.crt"; then
    run update-ca-certificates || true
  fi
fi

#
# RHEL / p11-kit style
#
if command -v update-ca-trust >/dev/null 2>&1; then
  log "Detected update-ca-trust"
  if install_anchor "$CA_TRUST_CERT" "/etc/pki/ca-trust/source/anchors/${name}.crt"; then
    run update-ca-trust extract || true
  fi
fi

#
# Arch / pure p11-kit style
#
if command -v trust >/dev/null 2>&1; then
  log "Detected trust"
  if install_anchor "$CA_TRUST_CERT" "/etc/ca-certificates/trust-source/anchors/${name}.crt"; then
    run trust extract-compat || true
  fi
fi

if [ "$installed" = "1" ]; then
  log "CA trust installation completed successfully"
else
  log "CA trust not installed into OS trust store; using env-based CA variables only"
fi

if [ "$#" -gt 0 ]; then
  log "Executing wrapped command: $*"
  exec "$@"
fi

log "No command provided to execute; exiting successfully"
exit 0
