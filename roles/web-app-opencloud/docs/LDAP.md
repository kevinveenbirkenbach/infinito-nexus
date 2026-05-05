# LDAP integration

OpenCloud uses the central `svc-db-openldap` instance for user and group lookups. Configuration is rendered into the role's environment file at deploy time using the `LDAP` group_var dictionary; no values are hard-coded.

## Variable mapping

| OpenCloud env | Group var |
|---|---|
| `OC_LDAP_URI` | `LDAP.SERVER.URI` |
| `OC_LDAP_BIND_DN` | `LDAP.DN.ADMINISTRATOR.DATA` |
| `OC_LDAP_BIND_PASSWORD` | `LDAP.BIND_CREDENTIAL` (Vault) |
| `OC_LDAP_USER_BASE_DN` | `LDAP.DN.OU.USERS` |
| `OC_LDAP_GROUP_BASE_DN` | `LDAP.DN.OU.GROUPS` |
| `OC_LDAP_USER_SCHEMA_USERNAME` | `LDAP.USER.ATTRIBUTES.ID` |
| `OC_LDAP_USER_SCHEMA_MAIL` | `LDAP.USER.ATTRIBUTES.MAIL` |
| `OC_LDAP_USER_SCHEMA_DISPLAY_NAME` | `LDAP.USER.ATTRIBUTES.FULLNAME` |

## Read-only mode

`GRAPH_LDAP_SERVER_WRITE_ENABLED=false` — OpenCloud must not modify the directory; user lifecycle is owned by the LDAP/Keycloak side.

## Inspect LDAP entries from inside the container

```bash
make exec CMD="docker exec opencloud opencloud users list"
```
