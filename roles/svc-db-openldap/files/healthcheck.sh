#!/usr/bin/env bash
set -euo pipefail

# 1) LDAP listener reachable
ldapsearch -x -H ldap://127.0.0.1:389 -s base -b "" "(objectClass=*)" dn >/dev/null 2>&1

# 2) memberof overlay exists (cn=config via ldapi EXTERNAL)
ldapsearch -Q -Y EXTERNAL -H ldapi:/// -LLL \
  -b "cn=config" "(&(objectClass=olcOverlayConfig)(olcOverlay=memberof))" dn \
  | grep -q "^dn:"
