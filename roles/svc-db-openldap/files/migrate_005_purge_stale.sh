#!/usr/bin/env bash
# Migration 005: purge stale pre-005 nested RBAC entries from OpenLDAP.
# Idempotent: prints MIGRATION_005_PURGED:<n> on rewrite, MIGRATION_005_NO_STALE otherwise.
#
# Args:
#   $1 OPENLDAP_CONTAINER  -- container name
#   $2 ROLES_BASE          -- ou=roles base DN
#   $3 BIND_DN             -- LDAP bind DN
#   $4 BIND_PW             -- LDAP bind password
#
# See docs/requirements/005-wordpress-multisite-rbac.md.
set -o pipefail

OPENLDAP_CONTAINER="${1:?OPENLDAP_CONTAINER required}"
ROLES_BASE="${2:?ROLES_BASE required}"
BIND_DN="${3:?BIND_DN required}"
BIND_PW="${4:?BIND_PW required}"

# Any direct child of ou=roles that is an organizationalUnit is an
# early-005 app OU container; everything under it must go too.
STALE_OUS=$(container exec "${OPENLDAP_CONTAINER}" ldapsearch -LLL -x \
  -H ldap://127.0.0.1:389 \
  -D "${BIND_DN}" \
  -w "${BIND_PW}" \
  -b "${ROLES_BASE}" \
  -s one \
  "(objectClass=organizationalUnit)" \
  dn 2>/dev/null | awk '/^dn: /{sub(/^dn: /,""); print}')

REMOVED=0
while IFS= read -r app_ou; do
  [[ -z "${app_ou}" ]] && continue
  # Delete children first (longest DN first so leaves go before parents).
  CHILDREN=$(container exec "${OPENLDAP_CONTAINER}" ldapsearch -LLL -x \
    -H ldap://127.0.0.1:389 \
    -D "${BIND_DN}" \
    -w "${BIND_PW}" \
    -b "${app_ou}" \
    -s sub \
    "(objectClass=*)" \
    dn 2>/dev/null | awk '/^dn: /{sub(/^dn: /,""); print}' | grep -v "^${app_ou}\$" || true)
  echo "${CHILDREN}" | awk '{print length, $0}' | sort -k1,1nr | awk '{$1=""; sub(/^ /,""); print}' | while IFS= read -r child; do
    [[ -z "${child}" ]] && continue
    container exec "${OPENLDAP_CONTAINER}" ldapdelete -x \
      -H ldap://127.0.0.1:389 \
      -D "${BIND_DN}" \
      -w "${BIND_PW}" \
      "${child}" 2>/dev/null || true
  done
  container exec "${OPENLDAP_CONTAINER}" ldapdelete -x \
    -H ldap://127.0.0.1:389 \
    -D "${BIND_DN}" \
    -w "${BIND_PW}" \
    "${app_ou}" 2>/dev/null || true
  REMOVED=$((REMOVED+1))
done <<< "${STALE_OUS}"

# Any DN-nested groupOfNames with a cn=..,cn=..,ou=roles pattern is an
# early-005 leftover (the final layout has no DN nesting).
STALE_NESTED=$(container exec "${OPENLDAP_CONTAINER}" ldapsearch -LLL -x \
  -H ldap://127.0.0.1:389 \
  -D "${BIND_DN}" \
  -w "${BIND_PW}" \
  -b "${ROLES_BASE}" \
  -s sub \
  "(objectClass=groupOfNames)" \
  dn 2>/dev/null | awk '/^dn: /{sub(/^dn: /,""); print}' | grep -E "^cn=[^,]+,cn=" || true)

echo "${STALE_NESTED}" | awk '{print length, $0}' | sort -k1,1nr | awk '{$1=""; sub(/^ /,""); print}' | while IFS= read -r nested; do
  [[ -z "${nested}" ]] && continue
  container exec "${OPENLDAP_CONTAINER}" ldapdelete -x \
    -H ldap://127.0.0.1:389 \
    -D "${BIND_DN}" \
    -w "${BIND_PW}" \
    "${nested}" 2>/dev/null || true
  REMOVED=$((REMOVED+1))
done

if [[ "${REMOVED}" -gt 0 ]]; then
  echo "MIGRATION_005_PURGED:${REMOVED}"
else
  echo "MIGRATION_005_NO_STALE"
fi
