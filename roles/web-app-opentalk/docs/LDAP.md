# LDAP integration (transitive)

OpenTalk does **not** open LDAP connections itself. Instead it relies on Keycloak's LDAP federation (`svc-db-openldap` is mapped into the central Keycloak realm) and queries Keycloak's admin Web API for user lookups. This avoids dual-source-of-truth problems and keeps LDAP credentials away from the OpenTalk service account.

## Chain

1. `svc-db-openldap` is the directory of record (users + groups).
2. Keycloak's `LDAP user federation` mirrors users into the realm (read-only).
3. OpenTalk controller authenticates users via OIDC and resolves invitee searches via `https://<keycloak>/admin/realms/<realm>/users?search=…`.

## Why no direct OC_LDAP_ binding

Upstream OpenTalk only ships `keycloak_webapi` and (legacy) `disabled` as `[user_search].backend` values. There is no native LDAP backend, so directly binding OpenTalk to OpenLDAP would require a custom backend not currently maintained.

## Inspect the Keycloak ↔ LDAP federation

```bash
make exec CMD="container exec keycloak /opt/keycloak/bin/kcadm.sh get components -r {{ OIDC.CLIENT.REALM }} --query type=org.keycloak.storage.UserStorageProvider"
```

If users created in OpenLDAP do not appear in OpenTalk, force a Keycloak full sync (component IDs vary per environment):

```bash
make exec CMD="container exec keycloak /opt/keycloak/bin/kcadm.sh create user-storage/<id>/sync?action=triggerFullSync -r {{ OIDC.CLIENT.REALM }}"
```
