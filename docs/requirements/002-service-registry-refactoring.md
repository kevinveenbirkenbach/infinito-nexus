# 001 - Service Registry Refactoring

## User Story

As a contributor, I want service configuration to be fully role-local so that
`group_vars/all/20_services.yml` is no longer needed and every role is
self-describing.

## Acceptance Criteria

- [x] `group_vars/all/20_services.yml` is deleted; no role or plugin reads from it.
- [x] Every service role declares its service metadata in its own `config/main.yml`
      under `compose.services.<entity_name>` (with optional `provides:`, `canonical:`)
      instead of in the central registry.
- [x] Load order *within* the same deploy type (universal, workstation, server) is
      declared via a custom `run_after:` list in the role's `meta/main.yml`. Each
      entry is a role name (e.g. `web-svc-cdn`). `roles/sys-utils-service-loader`
      MUST read this field and load the listed roles before the declaring role within
      the same deploy-type pass. This is a project-specific convention — Ansible does
      not process `run_after:` natively.
      Cross-type dependencies are handled implicitly by stage ordering:
      `roles/sys-utils-service-loader` runs in the constructor stage and loads all
      services (databases, `web-app-keycloak` via `provides: oidc`, etc.) before
      apps are deployed in the server stage. Apps MUST NOT declare `run_after:`
      entries for services of a different deploy type. If a role declares such a
      cross-type dependency, `roles/sys-utils-service-loader` MUST fail hard with a
      clear error instead of ignoring it. Apps MUST NOT require the user to list
      those dependencies explicitly in `APPS`.
- [x] The special `role_template: "svc-db-{type}"` database loading logic is removed;
      PostgreSQL and MariaDB are defined as regular services in their own
      `config/main.yml` (same as any other service). Because databases are a different
      deploy type from apps, they are loaded automatically before apps by
      `roles/sys-utils-service-loader` — no `run_after:` declaration is needed in
      the app.

      **Before:**
      ```yaml
      # group_vars/all/20_services.yml
      SERVICE_REGISTRY:
        database:
          role_template: "svc-db-{type}"   # resolved at runtime from app config
          type: backend

      # web-app-matomo/config/main.yml
      compose:
        services:
          database:
            shared: true
            type: "mariadb"   # drives role_template resolution
            enabled: true
      ```

      **After:**
      ```yaml
      # svc-db-mariadb/config/main.yml  — self-describing, no central registry entry
      compose:
        services:
          mariadb:
            shared: true
            enabled: true

      # svc-db-postgres/config/main.yml
      compose:
        services:
          postgres:
            shared: true
            enabled: true

      # web-app-matomo/config/main.yml  — no database.type needed for service loading
      # (svc-db-mariadb is loaded automatically before web-app-* by the service loader)
      ```
- [x] `frontend` / `backend` type is auto-detected from the role name prefix
      (`web-app-*`, `web-svc-*` → frontend; everything else → backend). The
      `type:` field for this purpose is removed from role `config/main.yml`.
      No legacy support is kept for role-local service metadata that still declares
      this `type:` field.
- [x] `canonical` aliases are declared under `compose.services.<entity_name>.canonical`
      in the role's `config/main.yml`, where `<entity_name>` is the entity name
      returned by the existing `get_entity_name` function for that role
      (e.g. `web-svc-cdn` exposes the primary entity `cdn` plus the alias
      entities `css` and `javascript`):
      ```yaml
      compose:
        services:
          cdn:
            shared: true
            enabled: true
          css:
            shared: true
            enabled: true
            canonical: cdn
          javascript:
            shared: true
            enabled: true
            canonical: cdn
      ```
- [x] A role MAY declare an optional `provides:` field under its primary service entry
      in `config/main.yml`. When present, `roles/sys-utils-service-loader` registers
      the role under that functional name instead of the entity name returned by
      `get_entity_name`. Roles without `provides:` are registered under their entity
      name by default. `provides:` MUST only be declared when the desired functional
      name differs from the entity name; otherwise the role MUST rely on the default
      entity name and omit `provides:`. Examples:
      ```yaml
      # web-app-keycloak/config/main.yml
      compose:
        services:
          keycloak:
            shared: true
            enabled: true
            provides: oidc

      # web-app-mailu/config/main.yml
      compose:
        services:
          mailu:
            shared: true
            enabled: true
            provides: email

      # svc-db-openldap/config/main.yml
      compose:
        services:
          openldap:
            shared: true
            enabled: true
            provides: ldap
      ```
      All consumers (templates, lookups, `run_after:` lists) continue to reference
      the functional name (e.g. `oidc`, `email`, `ldap`) — no consumer changes are
      required for roles that already use these names.
- [x] `roles/sys-utils-service-loader` is the single place that loads all services.
      It MUST use the existing function that determines which roles are universal,
      workstation, or server to derive the load order: universal roles first,
      then `web-svc-*`, then `web-app-*`.
- [x] `roles/sys-utils-service-loader` is invoked from the constructor stage
      (`tasks/stages/01_constructor.yml`) instead of the server block
      (`tasks/stages/02_server.yml`).
- [x] All service dependencies — including databases (e.g. `svc-db-mariadb`,
      `svc-db-postgres`) and shared services (e.g. `web-app-keycloak`) — are loaded
      automatically by `roles/sys-utils-service-loader` in the constructor stage.
      No service dependency MUST ever require the user to list it explicitly in `APPS`.
- [x] Every file that currently reads from `SERVICE_REGISTRY` or `20_services.yml`
      MUST be updated to discover service metadata from role `config/main.yml` files
      instead. This includes at minimum:
      - `plugins/lookup/service.py`
      - `plugins/lookup/applications_current_play.py`
      - any filter plugin, task, or template that references `SERVICE_REGISTRY`
- [x] New unit and integration tests MUST be written for the service discovery
      mechanism that replaces `SERVICE_REGISTRY`. Follow the rules in
      [testing.md](../agents/action/testing.md),
      [unit.md](../contributing/actions/testing/unit.md), and
      [integration.md](../contributing/actions/testing/integration.md).
      Tests MUST cover at minimum:
      - Discovery of `provides:`, `canonical:`, `shared:`, `enabled:` from role
        `config/main.yml`
      - Correct load order produced by `sys-utils-service-loader`
      - `get_entity_name` derivation for all relevant role name prefixes
      - `run_after:` ordering within the same deploy type
- [x] Every file and role that is modified as part of this refactoring MUST also be
      simplified and refactored where possible, following the principles in
      [principles.md](../contributing/design/principles.md). Do not limit changes to
      the minimum required — use the mandatory touch as an opportunity to improve
      clarity, reduce duplication, and remove dead code in the same pass.
- [x] All existing integration and unit tests pass after the refactoring.
- [x] Once all other Acceptance Criteria are checked off and the full validation
      app set deploys successfully, `docs/contributing/code/services.md` MUST be
      updated to reflect the new role-local configuration model. The update MUST
      follow the documentation guidelines in
      [documentation.md](../contributing/documentation.md).

## Validation Apps

The following app selection MUST be used to validate the refactoring end to end.
It covers all relevant service categories and dependency patterns:

| App | Purpose |
|---|---|
| `web-svc-cdn` | Frontend svc with canonical aliases (`css`, `javascript`) |
| `web-svc-file` | Simplest frontend svc — baseline auto-detection |
| `web-app-dashboard` | Frontend web-app consuming multiple services |
| `svc-db-postgres` | Database as a regular service (replaces `role_template`) — deployed standalone to verify the DB-as-service pattern directly |
| `svc-db-mariadb` | MariaDB as a regular service — deployed standalone alongside postgres to verify both database types independently |
| `web-app-matomo` | web-app with MariaDB dependency — tests automatic cross-type service loading |
| `web-app-gitea` | web-app with Keycloak (OIDC) dependency |
| `web-app-nextcloud` | Complex app with both MariaDB and Keycloak — depends on all of the above |

```bash
APPS="web-svc-cdn web-svc-file web-app-dashboard svc-db-postgres svc-db-mariadb web-app-matomo web-app-gitea web-app-nextcloud" \
  make deploy-fresh-purged-apps
```

## Prerequisites

Before starting any implementation work, you MUST read [AGENTS.md](../../AGENTS.md)
and follow all instructions in it.

## Implementation Strategy

Iterate over each app individually, starting with the most complex and working down to the simplest.
Every app in the Validation Apps table MUST be deployed standalone at least once during the iteration.
After completing one full iteration cycle over all apps, restart from the top until every app works
and all Acceptance Criteria are checked off.

**Iteration order (largest → smallest):**

1. `web-app-nextcloud` — most complex; MariaDB + Keycloak + many service dependencies
2. `web-app-gitea` — Keycloak (OIDC) dependency
3. `web-app-matomo` — MariaDB dependency — tests automatic cross-type service loading
4. `web-app-dashboard` — frontend web-app consuming multiple services
5. `svc-db-postgres` — database as a regular service
6. `svc-db-mariadb` — MariaDB as a regular service, standalone validation
7. `web-svc-cdn` — canonical aliases (`css`, `javascript`)
8. `web-svc-file` — simplest frontend service; baseline

**Per-app cycle:**

For every app in the iteration order, run the full loop described in
[iteration.md](../agents/action/iteration.md) independently — as if starting fresh for
that app. Do not carry over assumptions from the previous app.

1. Read [iteration.md](../agents/action/iteration.md) before starting each app.
2. Implement the role-local changes for the current app.
3. Deploy: `make deploy-fresh-purged-apps APPS=<role>`
4. Follow the inspect-fix-redeploy loop from [iteration.md](../agents/action/iteration.md) until the app works end to end.
5. Run `make test` — all tests MUST pass before moving to the next app.
6. Check off the relevant Acceptance Criteria above if fully covered by this app.

Repeat the full cycle from `web-app-nextcloud` down to `web-svc-file` until every criterion is checked.

## Out-of-Scope Changes (Stashed)

The following changes in `roles/web-app-nextcloud/` were identified as unrelated to this requirement and were unstaged and stashed for later handling:

- `tasks/_plugin_a_routines.yml` — tarball-based plugin install (DinD IPv6 workaround)
- `tasks/_plugin_install_from_tarball.yml` *(new)* — tarball install task file
- `tasks/main.yml` — Nextcloud appstore metadata fetch for plugin compatibility
- `templates/config/apps_paths.config.php.j2` *(new)* — `custom_apps` path registration

**Stash name:** `nextcloud: tarball plugin install (unrelated to req-001)`  
**Machine:** `msi-stealth-gs66`

### `roles/web-svc-coturn/`

- `templates/compose.yml.j2` — Coturn 4.9 fix: collapse IPv4/IPv6 `--external-ip` flags into one and replace `turnutils_stunclient` healthcheck with `pgrep`

**Stash name:** `coturn: fix external-ip IPv4/IPv6 and healthcheck (unrelated to req-001)`  
**Machine:** `msi-stealth-gs66`
