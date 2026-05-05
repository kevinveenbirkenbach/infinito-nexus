# Identity and Access Management

OpenCloud delegates authentication to the central Keycloak realm (OIDC) and consumes user/group data from the central OpenLDAP directory. Local password login is suppressed when `services.oidc.enabled: true` (the default), and accounts are auto-provisioned on first OIDC login.

## OIDC

- Issuer: `{{ OIDC.CLIENT.ISSUER_URL }}`
- Client ID: shared `OIDC.CLIENT.ID` (single Keycloak client per realm covers every web-app)
- Username claim: `preferred_username` → mapped to OpenCloud `username`
- Role claim: `groups` (Keycloak group memberships flow into OpenCloud roles)
- Auto-provisioning: enabled (`PROXY_AUTOPROVISION_ACCOUNTS=true`)
- Built-in IdP excluded: `OC_EXCLUDE_RUN_SERVICES=idp`

### Verify OIDC discovery

```bash
make exec CMD="curl -fsS {{ OIDC.CLIENT.DISCOVERY_DOCUMENT }}"
```

## LDAP

OpenCloud reads users from the central `svc-db-openldap` service.

- URI: `{{ LDAP.SERVER.URI }}`
- Bind DN: `{{ LDAP.DN.ADMINISTRATOR.DATA }}`
- User base DN: `{{ LDAP.DN.OU.USERS }}`
- Group base DN: `{{ LDAP.DN.OU.GROUPS }}`
- User filter: `(objectclass=inetOrgPerson)`
- Group filter: `(objectclass=groupOfNames)`

The `application_administrators` group (per requirement 004) gives OpenCloud admin rights when its members log in.

### Verify LDAP wiring

```bash
make exec CMD="docker exec opencloud opencloud config get ldap"
```

## Federation note

If a Keycloak user is not present in OpenLDAP, OpenCloud autoprovisions them on first login using the `preferred_username` claim. To guarantee stable usernames across Nextcloud, OpenCloud, and OpenTalk, all three apps share the same `OIDC.CLIENT.REALM` and the same `LDAP.DN.OU.USERS` source.
