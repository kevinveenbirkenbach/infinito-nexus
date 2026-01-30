#!/usr/bin/env sh
set -eu

: "${CA_TRUST_CERT:?CA_TRUST_CERT env var must be set (path to CA cert)}"
: "${CA_TRUST_NAME:?CA_TRUST_NAME env var must be set (trust anchor name)}"

if [ ! -r "$CA_TRUST_CERT" ]; then
  echo "[with-ca-trust] CA certificate not readable: $CA_TRUST_CERT" >&2
  exit 2
fi

# Sanitize trust name to a safe filename
name="$(printf '%s' "$CA_TRUST_NAME" | tr -c 'A-Za-z0-9._-' '_' )"
if [ -z "$name" ]; then
  echo "[with-ca-trust] CA_TRUST_NAME resolved to empty after sanitization." >&2
  exit 4
fi

install_ca_debian_like() {
  dst="/usr/local/share/ca-certificates/${name}.crt"
  mkdir -p "$(dirname "$dst")"
  cp -f "$CA_TRUST_CERT" "$dst"
  update-ca-certificates >/dev/null
}

install_ca_rhel_like() {
  dst="/etc/pki/ca-trust/source/anchors/${name}.crt"
  mkdir -p "$(dirname "$dst")"
  cp -f "$CA_TRUST_CERT" "$dst"
  update-ca-trust extract >/dev/null
}

install_ca_arch_like() {
  dst="/etc/ca-certificates/trust-source/anchors/${name}.crt"
  mkdir -p "$(dirname "$dst")"
  cp -f "$CA_TRUST_CERT" "$dst"
  trust extract-compat >/dev/null
}

if command -v update-ca-certificates >/dev/null 2>&1; then
  install_ca_debian_like
elif command -v update-ca-trust >/dev/null 2>&1; then
  install_ca_rhel_like
elif command -v trust >/dev/null 2>&1; then
  install_ca_arch_like
else
  echo "[with-ca-trust] No CA update tool found." >&2
  exit 3
fi

# Optional: run a command (container use-case)
if [ "$#" -gt 0 ]; then
  exec "$@"
fi
