#!/bin/bash
# Create or update the per-application group-ldap-mapper named
# `ldap-roles-<APP_ID>`. Echoes the mapper id on stdout.
#
# Required env:
#   KC_CONTAINER         keycloak container name
#   KC_REALM             realm name
#   LDAP_COMPONENT_ID    Keycloak LDAP component id (parentId)
#   APP_ID               application id
#   APP_GROUP_ID         Keycloak group id for /<root>/<APP_ID>
#   APP_GROUP_PATH       e.g. /roles/web-app-wordpress
#   LDAP_ROLES_DN        e.g. ou=roles,dc=infinito,dc=example
set -o pipefail
: "${KC_CONTAINER:?KC_CONTAINER is required}"
: "${KC_REALM:?KC_REALM is required}"
: "${LDAP_COMPONENT_ID:?LDAP_COMPONENT_ID is required}"
: "${APP_ID:?APP_ID is required}"
: "${APP_GROUP_ID:?APP_GROUP_ID is required}"
: "${APP_GROUP_PATH:?APP_GROUP_PATH is required}"
: "${LDAP_ROLES_DN:?LDAP_ROLES_DN is required}"

MAPPER_NAME="ldap-roles-$APP_ID"

container exec -i "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh get components \
  -r "$KC_REALM" \
  -q "parentId=$LDAP_COMPONENT_ID" \
  -q providerId=group-ldap-mapper \
  -q max=500 --fields id,name --format csv --noquotes 2>/dev/null \
  > /tmp/kc_mappers_listing.txt

EXISTING_ID=$(awk -F',' -v n="$MAPPER_NAME" \
  '!/^\[/ && !/Cgroup/ && $2==n {print $1; exit}' \
  /tmp/kc_mappers_listing.txt | tr -d '\r')

cat > /tmp/kc_mapper_payload.json <<PAYLOAD
{
  "name": "$MAPPER_NAME",
  "providerId": "group-ldap-mapper",
  "providerType": "org.keycloak.storage.ldap.mappers.LDAPStorageMapper",
  "parentId": "$LDAP_COMPONENT_ID",
  "config": {
    "membership.attribute.type": ["DN"],
    "group.name.ldap.attribute": ["description"],
    "membership.user.ldap.attribute": ["dn"],
    "preserve.group.inheritance": ["false"],
    "groups.dn": ["$LDAP_ROLES_DN"],
    "mode": ["LDAP_ONLY"],
    "user.roles.retrieve.strategy": ["LOAD_GROUPS_BY_MEMBER_ATTRIBUTE"],
    "groups.ldap.filter": ["(&(objectClass=groupOfNames)(cn=$APP_ID-*))"],
    "membership.ldap.attribute": ["member"],
    "ignore.missing.groups": ["true"],
    "group.object.classes": ["groupOfNames"],
    "memberof.ldap.attribute": ["memberOf"],
    "drop.non.existing.groups.during.sync": ["true"],
    "groups.path.group": ["$APP_GROUP_ID"],
    "groups.path": ["$APP_GROUP_PATH"]
  }
}
PAYLOAD

if [ -n "$EXISTING_ID" ]; then
  sed -i "s|\"name\":|\"id\": \"$EXISTING_ID\",\n    \"name\":|" /tmp/kc_mapper_payload.json
  # The keycloak container does not see the host path; stream the
  # payload via stdin instead of `-f /tmp/...`.
  cat /tmp/kc_mapper_payload.json \
    | container exec -i "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh update \
        "components/$EXISTING_ID" -r "$KC_REALM" -f - \
    >/dev/null 2>&1 || true
  printf '%s\n' "$EXISTING_ID"
else
  cat /tmp/kc_mapper_payload.json \
    | container exec -i "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh create \
        components -r "$KC_REALM" -f - -i 2>/dev/null \
    > /tmp/kc_create_mapper.txt
  grep -vE '(^\[|Cgroup)' /tmp/kc_create_mapper.txt \
    | grep -E '^[0-9a-fA-F-]{8,}$' | head -1 | tr -d '\r'
fi
