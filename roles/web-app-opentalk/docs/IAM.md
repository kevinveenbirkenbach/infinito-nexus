# Identity and Access Management

OpenTalk authenticates users against the central Keycloak realm via OIDC and looks up users via Keycloak's admin Web API (`keycloak_webapi` backend), so OpenLDAP feeds OpenTalk transitively through Keycloak.

## OIDC

- Issuer: `{{ OIDC.CLIENT.ISSUER_URL }}`
- Frontend client ID: `{{ OIDC.CLIENT.ID }}` (shared with the rest of the platform)
- Controller client ID/secret: same shared Keycloak client; secret pulled from the central OIDC vault entry

## User search

```toml
[user_search]
backend = "keycloak_webapi"
api_base_url = "{{ OPENTALK_KEYCLOAK_BASE_URL }}/admin/realms/{{ OIDC.CLIENT.REALM }}"
users_find_behavior = "from_user_search_backend"
```

OpenTalk does not access OpenLDAP directly. The chain is:

```
OpenLDAP  ─►  Keycloak (LDAP federation)  ─►  OpenTalk (Keycloak admin API)
```

This means: any user that exists in OpenLDAP and is reflected into the Keycloak realm can authenticate to OpenTalk and is autoprovisioned in the OpenTalk database on first login. The username equals the LDAP `uid` (delivered via the `preferred_username` claim).

## Admin role mapping

Members of the `application_administrators` LDAP group (per requirement 004) receive `groups` claims that OpenTalk maps to elevated permissions. The exact role-to-group mapping is configured via the controller's role policy file or the Keycloak realm role mapper.

## Verify discovery

```bash
make exec CMD="curl -fsS {{ OIDC.CLIENT.DISCOVERY_DOCUMENT }}"
```

## Verify Keycloak admin API access

```bash
make exec CMD="curl -fsS -H 'Authorization: Bearer <token>' {{ OPENTALK_KEYCLOAK_BASE_URL }}/admin/realms/{{ OIDC.CLIENT.REALM }}/users?search=alice"
```
