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

install_anchor() {
  src="$1"
  dst="$2"

  log "Installing CA anchor: $dst"
  run mkdir -p "$(dirname "$dst")"
  run cp -f "$src" "$dst"
  installed=1
}

#
# Debian / Ubuntu style
#
if command -v update-ca-certificates >/dev/null 2>&1; then
  log "Detected update-ca-certificates (Debian-like)"
  install_anchor "$CA_TRUST_CERT" "/usr/local/share/ca-certificates/${name}.crt"
  run update-ca-certificates
fi

#
# RHEL / p11-kit style
#
if command -v update-ca-trust >/dev/null 2>&1; then
  log "Detected update-ca-trust (RHEL / p11-kit)"
  install_anchor "$CA_TRUST_CERT" "/etc/pki/ca-trust/source/anchors/${name}.crt"
  run update-ca-trust extract
fi

#
# Arch / pure p11-kit style
#
if command -v trust >/dev/null 2>&1; then
  log "Detected trust (Arch / p11-kit)"

  install_anchor "$CA_TRUST_CERT" \
    "/etc/ca-certificates/trust-source/anchors/${name}.crt"

  # Also cover RHEL-style path if present
  install_anchor "$CA_TRUST_CERT" \
    "/etc/pki/ca-trust/source/anchors/${name}.crt"

  run trust extract-compat
fi

if [ "$installed" = "0" ]; then
  echo "[with-ca-trust] ERROR: No known CA trust mechanism found on this system" >&2
  exit 3
fi

log "CA trust installation completed successfully"

# Optional exec (container wrapper mode)
if [ "$#" -gt 0 ]; then
  log "Executing wrapped command: $*"
  exec "$@"
fi
