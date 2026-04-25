# RBAC 🛂

This page is the design SPOT for the Infinito.Nexus RBAC layer that provisions LDAP groups, synchronises them to Keycloak, and emits them as the OIDC `groups` claim. For IAM fundamentals that span both providers, see [common.md](common.md). For the LDAP server layer, see [ldap.md](ldap.md). For the OIDC client layer, see [oidc.md](oidc.md). Operator-facing steps live in [rbac.md](../../../administration/configuration/rbac.md).

## LDAP layout contract 🌳

Every role that declares an `rbac:` block in its `config/main.yml` is provisioned under a per-application OU under the container named by `RBAC.GROUP.NAME` (default `roles`):

```
ou=<application_id>,ou=roles,<LDAP_DN_BASE>
```

Role groups hang off that OU as `cn=<role_name>` entries. Tenant-aware applications (`rbac.tenancy.axis == "domain"`) add a tenant layer between the application OU and the role entries:

```
cn=<role_name>,ou=<application_id>,ou=roles,...                   # non-tenant role
cn=<role_name>,ou=<tenant_id>,ou=<application_id>,ou=roles,...    # tenant-aware per-tenant
cn=<role_name>,ou=<application_id>,ou=roles,...                   # tenant-aware scope=global
```

The pre-005 flat pattern `cn=<application_id>-<role_name>,ou=roles,...` MUST NOT appear in the tree after the 005 migration has run. [build_ldap_role_entries](../../../../roles/svc-db-openldap/filter_plugins/build_ldap_role_entries.py) is the authoritative producer; it also emits the intermediate OUs so the subtree is self-contained.

## `rbac.tenancy` schema 📐

```yaml
rbac:
  tenancy:
    axis:   "domain"                      # one of: "none" (default), "domain"
    source: "server.domains.canonical"    # Jinja path, only "server.domains.canonical" is implemented
  roles:
    <role_name>:
      description: "..."
      scope:  "per_tenant"                # one of: "per_tenant" (default), "global"
```

An application SHOULD opt in to `axis: domain` only when its authorisation model is genuinely per-tenant and the tenant axis is the canonical domain. Typical consumer: WordPress Multisite. Applications whose authorisation is one global user set (Nextcloud, Gitea, Keycloak itself) MUST keep `axis: none`.

## `rbac_group_path` lookup plugin 🧭

[rbac_group_path](../../../../plugins/lookup/rbac_group_path.py) is the **only** sanctioned way to derive the OIDC group path for an application role. Consumers MUST call it:

```jinja
# non-tenant app
"{{ lookup('rbac_group_path', application_id='web-app-yourls', role='administrator') }}"
# -> "roles/web-app-yourls/administrator"

# tenant-aware, per-tenant role
"{{ lookup('rbac_group_path', application_id='web-app-wordpress',
           role='editor', tenant='blog.example') }}"
# -> "roles/web-app-wordpress/blog.example/editor"

# tenant-aware, scope=global role
"{{ lookup('rbac_group_path', application_id='web-app-wordpress',
           role='network-administrator') }}"
# -> "roles/web-app-wordpress/network-administrator"
```

Inline `[RBAC.GROUP.NAME, ...] | path_join` is forbidden because it scatters the path shape across dozens of files and makes future layout changes partial. Centralising the path in the plugin guarantees that a layout evolution stays a one-file change.

## Keycloak group tree and the `groups` client scope 🎫

Keycloak imports the LDAP tree with `Preserve Group Inheritance = true`, so every `ou=<application_id>` appears as a Keycloak group with its role children as sub-groups and (for tenant-aware apps) tenant OUs as another sub-group layer.

The `groups` client scope emits the OIDC `groups` claim with `full.path=true`, so consumers receive entries shaped like:

```
/roles/web-app-nextcloud/administrator
/roles/web-app-wordpress/<tenant>/<role>
/roles/web-app-wordpress/network-administrator
```

The scope MUST be a **default** client scope on every OIDC client that needs group-based RBAC. Making it optional again reintroduces the userinfo regression that requirement 004 fixed: when optional with `include.in.token.scope=false`, Keycloak drops the group-membership mapper from userinfo even when the scope is explicitly requested, so consumers receive no groups and fall back to `subscriber`.

## See also 🔗

- [common.md](common.md)
- [ldap.md](ldap.md)
- [oidc.md](oidc.md)
- [Administration RBAC](../../../administration/configuration/rbac.md)
