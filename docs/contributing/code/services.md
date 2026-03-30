# Service Management

This page documents how services are defined, mapped, loaded, and injected at deploy time.

## What Is a Service?

A *service* is a shared dependency that one or more applications can opt into via their `compose.services.<key>` configuration.
Each service has:

- a **key** — the short name used inside `compose.services` (e.g. `cdn`, `logout`, `ldap`)
- a **role** — the Ansible role that provisions it (e.g. `web-svc-cdn`, `svc-db-openldap`)
- a **type** — either `frontend` (loaded by `sys-front-inj-all`) or `backend` (loaded by `sys-stk-backend`)

An application declares it needs a service by setting `compose.services.<key>.enabled: true` in its config.
A service is considered *shared* (reusable across applications) when it also sets `shared: true`.

## SPOT: Service Registry

The canonical service key → role mapping lives in [`group_vars/all/20_services.yml`](../../../group_vars/all/20_services.yml).
This is the **single source of truth** for all service mappings — add a new service here to register it system-wide.

It is an Ansible `group_vars` file, so the `services` variable is automatically available in all plays.
The Python CLI resolver reads the same file — no hardcoded mappings exist anywhere else.

```yaml
# group_vars/all/20_services.yml
services:
  matomo:
    role: web-app-matomo
    type: frontend
  ldap:
    role: svc-db-openldap
    type: backend
  database:
    role_template: "svc-db-{type}"   # {type} taken from compose.services.database.type
    type: backend
```

## Service Config per Role

Every role that provides a service defines its own compose.services block in:

```
roles/<role-name>/config/main.yml
  compose:
    services:
      <key>:
        enabled: true
        shared: true
```

## Two Independent Mechanisms

**Loading a service** and **injecting a service into an app's nginx config** are two separate concerns driven by the same config flag `compose.services.<key>.enabled`.

### 1. Loading (deploy the container)

Decides whether the service container is deployed at all.

#### Frontend services — `sys-front-inj-all`

[`roles/sys-front-inj-all/tasks/01_services.yml`](../../../roles/sys-front-inj-all/tasks/01_services.yml) is the **SPOT** for all frontend service loading.

It iterates over every entry with `type: frontend` from `20_services.yml` and for each:

1. Checks `lookup('service', item.key).needed` — is the service needed (enabled AND shared) by any deployed app?
2. Checks `run_once_*` — has the service already been loaded this run?
3. Checks `application_id != item.value.role` — don't load a service as its own dependency
4. Performs a reachability check via [`_load_frontend_service.yml`](../../../roles/sys-front-inj-all/tasks/_load_frontend_service.yml)
5. Loads the service via `utils/load_app.yml` if the endpoint is not reachable (status ≠ 200)

#### Backend services — `sys-stk-backend`

[`roles/sys-stk-backend/tasks/main.yml`](../../../roles/sys-stk-backend/tasks/main.yml) loops over a list of backend services and calls
[`_load_service.yml`](../../../roles/sys-stk-backend/tasks/_load_service.yml) for each, using the `service_should_load` lookup (checks `enabled AND shared`).

### 2. Injection (add service to the app's nginx config)

Decides whether a service is referenced inside an individual application's nginx vhost.
Controlled by `inj_enabled`, computed in [`roles/sys-front-inj-all/tasks/main.yml`](../../../roles/sys-front-inj-all/tasks/main.yml):

```yaml
inj_enabled: "{{ applications | inj_enabled(application_id, SRV_WEB_INJ_COMP_FEATURES_ALL) }}"
```

The `inj_enabled` filter ([`roles/sys-front-inj-all/filter_plugins/inj_enabled.py`](../../../roles/sys-front-inj-all/filter_plugins/inj_enabled.py))
reads `compose.services.<key>.enabled` for the **current app** and returns a dict of booleans.

Each injection role is then included conditionally:

| Condition | Role loaded |
|---|---|
| `inj_enabled.matomo` | `sys-front-inj-matomo` — adds Matomo tracking snippet |
| `inj_enabled.logout` | `sys-front-inj-logout` — adds logout proxy endpoint |
| `inj_enabled.dashboard` | `sys-front-inj-dashboard` — adds dashboard iframe notifier |
| `inj_enabled.css` | `sys-front-inj-css` — adds corporate CSS |
| `inj_enabled.javascript` | `sys-front-inj-javascript` — adds JS injection |

#### CSS injection (`inj_enabled.css`)

`sys-front-inj-css` injects a shared corporate stylesheet into the application's nginx vhost.
The stylesheet itself lives in each role under `files/style.css` and is served via the CDN service.
It applies a minimal token-based theme (using the `--color-01-*` palette) so all apps share a consistent look.

See the agent authoring guide for `style.css`: [`docs/agents/files/role/style.css.md`](../../../docs/agents/files/role/style.css.md)

#### JavaScript injection (`inj_enabled.javascript`)

`sys-front-inj-javascript` injects a shared JavaScript bundle into the application's nginx vhost.
The script lives in each role under `files/javascript.js` (or `templates/javascript.js.j2` for templated values).
It handles browser-side integration that cannot be solved via configuration or CSS alone — for example DOM mutations required to wire up dashboard or logout behaviour.

See the agent authoring guide for `javascript.js`: [`docs/agents/files/role/javascript.js.md`](../../../docs/agents/files/role/javascript.js.md)

**`lookup('service', ...)` does NOT add a service to the current domains.**
It only controls whether the service container is deployed.
The nginx domain injection is handled entirely by `inj_enabled` + the injection roles above.

## `load_app.yml` — run-once loader

File: [`tasks/utils/load_app.yml`](../../../tasks/utils/load_app.yml)

Loads a role exactly once by setting `application_id` to the target role name and calling `include_role`.
The `run_once_<role_underscored>` flag is set inside the loaded role itself (via `tasks/utils/once/flag.yml`)
to prevent duplicate loads across multiple app invocations.

## Lookup Plugins

### `service` — resolve a service and return its deployment flags

File: [`plugins/lookup/service.py`](../../../plugins/lookup/service.py)

```yaml
lookup('service', 'matomo')          # look up by service key
lookup('service', 'web-app-matomo')  # look up by role name (bidirectional)
```

- Reads `applications`, `group_names`, and `services` (from `group_vars/all/20_services.yml`) from Ansible variables
- Accepts either a service **key** (e.g. `matomo`) or a **role name** (e.g. `web-app-matomo`) as the term — both resolve to the same entry
- Returns a dict per term:

  | Field     | Type   | Meaning |
  |-----------|--------|---------|
  | `id`      | string | Canonical service key (e.g. `matomo`) |
  | `role`    | string | Provider role name (e.g. `web-app-matomo`) |
  | `enabled` | bool   | Any deployed app has `compose.services.<key>.enabled: true` |
  | `shared`  | bool   | Any deployed app has `compose.services.<key>.shared: true` |
  | `needed`  | bool   | Any deployed app has **both** `enabled` and `shared` (direct or transitively) |

- **Transitive:** `needed` follows chains of enabled services recursively, but the final target must have both `enabled: true` AND `shared: true`
- **Limitation:** transitive resolution only fires when the service key in `compose.services` equals a full application ID.
  Short keys (e.g. `collabora`) do not chain to `web-svc-collabora` — only the key `web-svc-collabora` would.
- Does **not** control nginx injection — see `inj_enabled` above
- Used in: [`roles/sys-front-inj-all/tasks/01_services.yml`](../../../roles/sys-front-inj-all/tasks/01_services.yml)
- Tests: [`tests/unit/plugins/lookup/test_service.py`](../../../tests/unit/plugins/lookup/test_service.py)

### `service_should_load` — should this service be loaded for the current app?

File: [`roles/sys-stk-backend/lookup_plugins/service_should_load.py`](../../../roles/sys-stk-backend/lookup_plugins/service_should_load.py)

```yaml
query('service_should_load', service_id, application_id=application_id, service_name=service_name) | first
```

- Checks `enabled AND shared` for a single `application_id`
- Guards against `run_once_*` already set and self-loading (`application_id == service_id`)
- Used in: [`roles/sys-stk-backend/tasks/_load_service.yml`](../../../roles/sys-stk-backend/tasks/_load_service.yml)
- Tests: [`tests/unit/roles/sys-stk-backend/lookup_plugins/test_service_should_load.py`](../../../tests/unit/roles/sys-stk-backend/lookup_plugins/test_service_should_load.py)

### `inj_enabled` filter — which injections are active for this app?

File: [`roles/sys-front-inj-all/filter_plugins/inj_enabled.py`](../../../roles/sys-front-inj-all/filter_plugins/inj_enabled.py)

```yaml
applications | inj_enabled(application_id, feature_list)
```

- Reads `compose.services.<feature>.enabled` for the current `application_id`
- Returns `{feature: bool}` dict used to gate injection roles
- Used in: [`roles/sys-front-inj-all/tasks/main.yml`](../../../roles/sys-front-inj-all/tasks/main.yml)

## Python CLI Resolver

File: [`cli/meta/applications/resolution/services/resolver.py`](../../../cli/meta/applications/resolution/services/resolver.py)

Reads `group_vars/all/20_services.yml` and resolves which provider roles an application needs,
following service dependencies transitively (BFS). Used by the CLI to compute deploy order and
dependency graphs.

- `resolve_direct_service_roles_from_config(config)` — roles needed directly by one app config
- `ServicesResolver.resolve_transitively(role_name)` — full BFS over transitive dependencies
- Tests: [`tests/unit/cli/meta/applications/resolution/services/test_resolver.py`](../../../tests/unit/cli/meta/applications/resolution/services/test_resolver.py)

## Related Files

| File | Purpose |
|---|---|
| [`group_vars/all/20_services.yml`](../../../group_vars/all/20_services.yml) | **SPOT** — service key → role mapping with `type: frontend/backend` |
| [`roles/sys-front-inj-all/tasks/01_services.yml`](../../../roles/sys-front-inj-all/tasks/01_services.yml) | **SPOT** — frontend service loading loop |
| [`roles/sys-front-inj-all/tasks/_load_frontend_service.yml`](../../../roles/sys-front-inj-all/tasks/_load_frontend_service.yml) | Reachability check + conditional load per frontend service |
| [`roles/sys-front-inj-all/tasks/main.yml`](../../../roles/sys-front-inj-all/tasks/main.yml) | Orchestrates loading + injection for every deployed app |
| [`roles/sys-front-inj-all/filter_plugins/inj_enabled.py`](../../../roles/sys-front-inj-all/filter_plugins/inj_enabled.py) | `inj_enabled` filter — per-app injection flags |
| [`tasks/utils/load_app.yml`](../../../tasks/utils/load_app.yml) | Run-once role loader |
| [`tasks/utils/once/flag.yml`](../../../tasks/utils/once/flag.yml) | Sets `run_once_<role>` fact to prevent duplicate loads |
| [`plugins/lookup/service.py`](../../../plugins/lookup/service.py) | Resolve service by key or role; returns `{id, role, enabled, shared, needed}` |
| [`roles/sys-stk-backend/lookup_plugins/service_should_load.py`](../../../roles/sys-stk-backend/lookup_plugins/service_should_load.py) | "Should service load for this app?" lookup |
| [`cli/meta/applications/resolution/services/resolver.py`](../../../cli/meta/applications/resolution/services/resolver.py) | Python-side service resolver (CLI use) |
| [`utils/config_utils.py`](../../../utils/config_utils.py) | `get_app_conf()` — hierarchical config accessor |
| [`roles/sys-stk-backend/tasks/main.yml`](../../../roles/sys-stk-backend/tasks/main.yml) | Backend service loading (ldap, ollama, oauth2) |
| [`roles/sys-stk-backend/tasks/_load_service.yml`](../../../roles/sys-stk-backend/tasks/_load_service.yml) | Single-service load helper for backend stack |
