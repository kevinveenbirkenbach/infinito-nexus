#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# Config (bootstrap only)
# -----------------------------------------------------------------------------
: "${LDAP_SUFFIX:=dc=infinito,dc=localhost}"
: "${LDAP_ROOT_DN:=cn=admin,${LDAP_SUFFIX}}"
: "${LDAP_ROOT_PW:=changeme}"

SLAPD_D_DIR="/etc/ldap/slapd.d"
DB_DIR="/var/lib/ldap"

bootstrap_needed() {
  [ ! -d "${SLAPD_D_DIR}" ] || [ -z "$(ls -A "${SLAPD_D_DIR}" 2>/dev/null)" ]
}

detect_module_path() {
  # Common Debian paths:
  # - /usr/lib/ldap
  # - /usr/lib/x86_64-linux-gnu/ldap
  # (also other multiarch variants)
  if [ -d /usr/lib/ldap ]; then
    echo "/usr/lib/ldap"
    return 0
  fi

  local p
  p="$(ls -d /usr/lib/*/ldap 2>/dev/null | head -n1 || true)"
  if [ -n "${p}" ] && [ -d "${p}" ]; then
    echo "${p}"
    return 0
  fi

  # Fallback: keep old default (won't crash bootstrap, but overlays might fail)
  echo "/usr/lib/ldap"
}

write_minimal_config() {
  local hash
  local module_path
  hash="$(slappasswd -s "${LDAP_ROOT_PW}")"
  module_path="$(detect_module_path)"

  rm -rf "${SLAPD_D_DIR:?}"/*
  mkdir -p "${SLAPD_D_DIR}" /run/slapd "${DB_DIR}"

  # Optional log (useful for debugging)
  echo "[openldap] detected olcModulePath: ${module_path}"

  # Global + module list
  cat <<EOF | slapadd -n 0 -F "${SLAPD_D_DIR}"
dn: cn=config
objectClass: olcGlobal
cn: config
olcPidFile: /run/slapd/slapd.pid
olcArgsFile: /run/slapd/slapd.args

dn: cn=module{0},cn=config
objectClass: olcModuleList
cn: module{0}
olcModulePath: ${module_path}
EOF

  # Core schemas (ldif form exists on Debian)
  slapadd -n 0 -F "${SLAPD_D_DIR}" -l /etc/ldap/schema/core.ldif
  slapadd -n 0 -F "${SLAPD_D_DIR}" -l /etc/ldap/schema/cosine.ldif
  slapadd -n 0 -F "${SLAPD_D_DIR}" -l /etc/ldap/schema/inetorgperson.ldif

  # MDB database
  cat <<EOF | slapadd -n 0 -F "${SLAPD_D_DIR}"
dn: olcDatabase={1}mdb,cn=config
objectClass: olcDatabaseConfig
objectClass: olcMdbConfig
olcDatabase: {1}mdb
olcSuffix: ${LDAP_SUFFIX}
olcRootDN: ${LDAP_ROOT_DN}
olcRootPW: ${hash}
olcDbDirectory: ${DB_DIR}
olcDbMaxSize: 1073741824
olcAccess: to * by dn.exact="${LDAP_ROOT_DN}" manage by * break
EOF

  chown -R openldap:openldap /run/slapd "${DB_DIR}" "${SLAPD_D_DIR}"
}

if bootstrap_needed; then
  echo "[openldap] bootstrap slapd.d + mdb for suffix ${LDAP_SUFFIX}"
  write_minimal_config
fi

exec /usr/sbin/slapd \
  -F "${SLAPD_D_DIR}" \
  -u openldap -g openldap \
  -h "ldap:/// ldapi:///" \
  -d 0
