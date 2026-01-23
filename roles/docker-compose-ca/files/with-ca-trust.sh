#!/usr/bin/env sh
set -eu

: "${CA_TRUST_CERT:?CA_TRUST_CERT env var must be set (path inside container to the mounted CA cert)}"

if [ ! -r "$CA_TRUST_CERT" ]; then
  echo "[with-ca-trust] CA certificate not readable: $CA_TRUST_CERT" >&2
  exit 2
fi

install_ca_debian_like() {
  dst="/usr/local/share/ca-certificates/infinito-root-ca.crt"
  mkdir -p "$(dirname "$dst")"
  cp -f "$CA_TRUST_CERT" "$dst"
  update-ca-certificates >/dev/null
}

install_ca_rhel_like() {
  dst="/etc/pki/ca-trust/source/anchors/infinito-root-ca.crt"
  mkdir -p "$(dirname "$dst")"
  cp -f "$CA_TRUST_CERT" "$dst"
  update-ca-trust extract >/dev/null
}

if command -v update-ca-certificates >/dev/null 2>&1; then
  install_ca_debian_like
elif command -v update-ca-trust >/dev/null 2>&1; then
  install_ca_rhel_like
else
  echo "[with-ca-trust] No CA update tool found (update-ca-certificates/update-ca-trust)." >&2
  exit 3
fi

if [ "$#" -lt 1 ]; then
  echo "[with-ca-trust] No command provided to execute after CA installation." >&2
  exit 4
fi

exec "$@"
