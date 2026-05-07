# Suppression Markers 🚫

The unified `# noqa` / `# nocheck` syntax that suppresses individual checks across the infinito-nexus test suite.

You MUST use these markers only when the check genuinely does not apply. You MUST NOT use them to silence legitimate issues.

## Grammar 📐

A suppression marker is a comment carrying one or more rule keys:

```
<comment-prefix> (noqa|nocheck): <rule>(, <rule>)*
```

Rules:

- `noqa` and `nocheck` are accepted as synonyms by the parser, but by repo convention every project rule MUST use `nocheck:`. Reason: `# noqa: <code>` is also parsed by ruff as a flake8 directive, and ruff warns on non-flake8 rule keys (every key in this catalog is project-specific, so the warning fires on every marker). `nocheck:` is the project-specific keyword ruff ignores. Reserve `noqa:` for real flake8 / ruff codes (`E402`, `F401`, …). The convention is enforced by [test_noqa_only_ruff_codes.py](../../../../tests/lint/repository/test_noqa_only_ruff_codes.py), which fails any `# noqa: <code>` whose codes don't match the ruff/flake8 shape `[A-Z]+\d+`.
- The keyword is matched **case-insensitively**.
- `<rule>` is a kebab-case identifier from the catalog below.
- Multiple rules MAY be combined on one comment, comma-separated: `# nocheck: shared, email`.

Accepted comment prefixes (so the marker fits any file format that the test scans):

| Prefix       | Use in                                  |
| ------------ | --------------------------------------- |
| `#`          | Python, YAML, shell, conf, INI, …       |
| `//`         | JS, JSONC, …                            |
| `{# … #}`    | Jinja2 templates                        |
| `<!-- … -->` | HTML, Markdown                          |

Implementation: [utils/annotations/suppress.py](../../../../utils/annotations/suppress.py).

## Position semantics 📍

The placement rule is per check. The catalog column "Position" uses these labels:

- **same line**: the marker MUST be on the same line as the construct it suppresses.
- **line above**: the marker MUST be on the immediately preceding non-empty line. Blank lines between the marker and the construct break the association.
- **same or above**: either of the above is accepted.
- **comment block above**: the marker may sit on any line in a contiguous comment block above the construct (no blank line between marker and construct).
- **head (first 30 lines)**: the marker MAY appear anywhere in the first 30 lines of the file. Used for file-level opt-outs that should stay visible at the top of the file.
- **anywhere**: the marker may appear on any line of the file. Used for whole-file opt-outs whose semantics legitimately apply to the entire file.

## Catalog 📚

| Rule                | Position            | Affected test                                                                                                                | Effect                                                                                                          |
| ------------------- | ------------------- | ---------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `url`               | same or above       | [test_urls_reachable.py](../../../../tests/external/repository/test_urls_reachable.py)                                       | Skips probing the literal HTTP(S) URL. Use for CDN roots and API base URLs that return 4xx without a path.       |
| `docker-version`    | line above          | [test_image_versions.py](../../../../tests/external/docker/test_image_versions.py)                                           | Skips the live version-update warning for that image's `version:` key.                                          |
| `direct-yaml`       | same line / span    | [test_no_direct_yaml_calls.py](../../../../tests/lint/repository/test_no_direct_yaml_calls.py)                               | Allows the marked `yaml.safe_load` / `safe_dump` call to bypass `utils.cache.yaml`. This rule's checker hard-rejects `noqa:` and accepts only `nocheck:` (ruff parses `noqa:` as flake8 and warns on non-flake8 codes). |
| `shared`            | comment block above | [test_service_shared_consistency.py](../../../../tests/lint/ansible/test_service_shared_consistency.py)                     | Marks a service whose `enabled: true` legitimately does not require `shared: true`.                              |
| `email`             | line above          | [test_email.py](../../../../tests/lint/ansible/roles/web-app/integration/test_email.py)                 | Suppresses the missing-email-integration warning when paired with `enabled: false` and `shared: false`.          |
| `logout`            | line above          | [test_logout_dashboard.py](../../../../tests/lint/ansible/roles/web-app/integration/test_logout_dashboard.py) | Opts a `web-app-*` role out of the universal-logout integration. Marker MUST be on the line directly above `logout:`, paired with `enabled: false` and `shared: false`. |
| `dashboard`         | line above          | [test_logout_dashboard.py](../../../../tests/lint/ansible/roles/web-app/integration/test_logout_dashboard.py) | Opts a `web-app-*` role out of the dashboard tile integration. Same shape as `logout`.                            |
| `oidc`              | line above          | [test_sso.py](../../../../tests/lint/ansible/roles/web-app/integration/test_sso.py)                     | Opts the role's native OIDC path out (so that `oauth2` must take over, OR — if `oauth2` is also opted out — the role legitimately has no login flow). Same shape as `email`. |
| `oauth2`            | line above          | [test_sso.py](../../../../tests/lint/ansible/roles/web-app/integration/test_sso.py)                     | Opts the role's oauth2-proxy path out. In combination with `# nocheck: oidc` it declares "this role has no login flow at all". Same shape as `email`. |
| `file-size`         | head (first 30 lines) | [test_python_file_size.py](../../../../tests/lint/repository/test_python_file_size.py)                                     | Opts the entire `.py` file out of the 500-line cap.                                                              |
| `run-once`          | anywhere            | [test_run_once_tags.py](../../../../tests/lint/ansible/test_run_once_tags.py), [test_schema.py](../../../../tests/integration/roles/run_once/test_schema.py) | Marks a role's `tasks/main.yml` as intentionally re-runnable; skips both the run-once tag check and the suffix check. |
| `run-once-suffix`   | same line           | [test_schema.py](../../../../tests/integration/roles/run_once/test_schema.py)                                                | Allows a single `when:` item to reference a `run_once_<other>` flag whose suffix differs from the current role.   |
| `raw-docker`        | same or above; head (first 30 lines) | [test_no_raw_docker.py](../../../../tests/integration/docker/test_no_raw_docker.py)                       | Marks a single line or a whole file under `roles/` as legitimately calling `docker` / `docker compose` / `docker-compose` directly. The check is scoped to `roles/`; bootstrap scripts and CI workflows outside `roles/` are not scanned and need no marker. |
| `hardcoded-dns-resolver` | same or above | [test_no_hardcoded_dns_resolvers.py](../../../../tests/lint/repository/test_no_hardcoded_dns_resolvers.py) | Marks a line that legitimately needs a literal IP from `NETWORK_PUBLIC_DNS_RESOLVERS` at the substitution point (CoreDNS `forward` directives that don't run through Jinja, host-bootstrap shell scripts, documentation examples). The variable in `group_vars/all/08_networks.yml` is the SPOT for these IPs everywhere else.   |
| `dynamic-flag`      | same line (per-flag) OR comment block above key (whole block) | [test_dynamic_flags.py](../../../../tests/integration/roles/meta/services/test_dynamic_flags.py)                  | Marks a `roles/*/meta/services.yml` flag whose value legitimately stays literal. Per-flag (same line) is the typical shape for databases (`enabled: true` literal, `shared` still dynamic). Block-level (comment block above the service key) is for entries where both flags stay literal (e.g. `css`). |
| `lookup-config-path`| same or above       | [tests/integration/lookups/config/](../../../../tests/integration/lookups/config/) (literal / variable / wildcard / role-local) | Skips a single `lookup('config', …)` call from every path-validation pass. Use when the call legitimately resolves at runtime against state that is NOT visible to the static scan, typically a self-referential role like `web-app-oauth2-proxy` reading `services.oauth2.*` keys that other roles publish but its own `meta/services.yml` does not. Note: the role-local pass already ignores any call whose app argument is NOT the literal `application_id` (e.g. `_BBB_COTURN_ROLE`, `oauth2_proxy_application_id`), so cross-role lookups need no marker for that pass. Mark a call only when the literal / variable / wildcard pass complains. |
| `unused-var`        | same or above       | [tests/lint/ansible/variables/test_role_and_group_vars_used.py](../../../../tests/lint/ansible/variables/test_role_and_group_vars_used.py) | Exempts a top-level key in `roles/<role>/{vars,defaults}/main.yml` or `group_vars/**/*.yml` from the "must be referenced in some `.yml` / `.yaml` / `.j2`" check. Use when the var is consumed somewhere the lint cannot see (Python plugin code, an external tool reading the rendered Ansible inventory, `set_fact` chains driven by computed names, etc.). Do NOT use to silence a legitimately dead var; prune the declaration instead. |
| `project-root-import`| same or above      | [tests/lint/repository/test_project_root_import.py](../../../../tests/lint/repository/test_project_root_import.py) | Permits a local `PROJECT_ROOT` / `parents[N]` / `os.pardir` chain on the marked line. Reserved for two cases: a `__main__.py` bootstrap shim that prepends the repo root to `sys.path` before any package import resolves, and a standalone script under `roles/<role>/files/` that has no package container to import from. The marker MUST carry an inline comment that explains why the local computation is unavoidable. |
| `domain-spot`       | same or above       | [tests/lint/repository/test_domain_primary_spot.py](../../../../tests/lint/repository/test_domain_primary_spot.py) | Marks a line that legitimately uses a `<word>.{{ DOMAIN_PRIMARY }}` host literal outside the SPOT (`roles/<role>/meta/server.yml` / `meta/variants.yml`). Use only for legacy domain cleanups (e.g. removing stale nginx config for a renamed host) where the canonical SPOT cannot represent the historical name. |
| `literal-protocol-lookup`| same or above  | [tests/lint/repository/test_literal_protocol_with_lookup.py](../../../../tests/lint/repository/test_literal_protocol_with_lookup.py) | Allows a hardcoded `http://` / `https://` literal next to a `lookup(...)` call. Reserved for legitimate internal cases where the protocol is genuinely fixed: Docker-network upstreams that always speak plaintext (`http://<container>:<port>`), loopback URLs in CI fixtures, and similar. Production-facing URLs MUST go through `lookup('tls', …, 'protocols.web')`. |

## Examples 💡

`url`, on the line carrying the literal URL or on the line above it:

```sh
ensure_proxy_repo raw raw-packagist "$(... https://repo.packagist.org/ ...)"  # nocheck: url
```

```yaml
# nocheck: url
api_base_url: "https://example.org/v1"
```

`docker-version`, directly above a `version:` key:

```yaml
service_x:
  # nocheck: docker-version
  version: "4.5"
```

`direct-yaml`, anywhere on the call's physical line or on any line spanned by the multi-line call. This rule MUST use `nocheck:` (not `noqa:`): ruff parses `# noqa: <code>` as a flake8 directive and warns about non-flake8 codes like `direct-yaml`.

```python
data = yaml.safe_load(text)  # nocheck: direct-yaml
```

`shared`, somewhere in the comment block immediately above a service key:

```yaml
# This service is inherently role-local.
# nocheck: shared
my_local_service:
  enabled: true
```

`email`, directly above the `email:` block, paired with both flags false:

```yaml
# nocheck: email
email:
  enabled: false
  shared: false
```

`file-size`, at the top of a long Python file:

```python
"""Module docstring."""
# nocheck: file-size  (single-host orchestration script ships as one file)
```

`run-once`, at the top of a role's `tasks/main.yml`:

```yaml
# nocheck: run-once

- name: ...
```

`run-once-suffix`, on the exact `when:` list-item line:

```yaml
when:
  - run_once_svc_db_openldap is not defined   # nocheck: run-once-suffix
```

`raw-docker`, per-line on a single role-task line that legitimately calls `docker` directly (e.g. a bootstrap step that runs before the `container` wrapper is on the path):

```yaml
- name: "Bootstrap engine before the wrapper exists"
  ansible.builtin.command: docker info  # nocheck: raw-docker
```

`raw-docker`, file-level at the top of a role's bundled shell script that legitimately drives the engine directly:

```sh
#!/usr/bin/env bash
# nocheck: raw-docker. Runs from sys-svc-container's installer before the wrapper symlink lands.
docker buildx build ...
```

`dynamic-flag`, two placements depending on scope:

Per-flag (same line), for databases where `enabled: true` reflects a static fact about the role's needs but `shared` still resolves dynamically:

```yaml
mariadb:
  enabled: true  # nocheck: dynamic-flag
  shared: "{{ 'svc-db-mariadb' in group_names }}"
```

Block-level (comment block above the service key), for service entries whose both flags legitimately stay literal (e.g. `css`, `javascript`):

```yaml
# nocheck: dynamic-flag
css:
  enabled: true
  shared: true
```

`project-root-import`, on the line that locally derives the repo root inside a `__main__.py` `sys.path` bootstrap (the marker line MUST explain why the local computation runs before any package import resolves), or inside a standalone script that has no package container to import from:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # nocheck: project-root-import, sys.path bootstrap before package imports resolve
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
```

`unused-var`, on the var declaration line (or directly above it), when the var is consumed by Python plugin code or another non-YAML/Jinja surface that the static scan cannot reach:

```yaml
# nocheck: unused-var  # consumed by plugins/filter/<role>_render.py
ROLE_TEMPLATE_PATH: "templates/<role>/render.j2"
```

```yaml
ROLE_TEMPLATE_PATH: "templates/<role>/render.j2"  # nocheck: unused-var  # consumed by plugins/filter/<role>_render.py
```

`lookup-config-path`, on the line carrying a `lookup('config', …)` call (or directly above it) when the path legitimately resolves against runtime-only state that the static scan cannot see, for example a self-referential role that consumes the `services.<self>.*` keys other roles publish about it:

```jinja
# nocheck: lookup-config-path
upstreams = {{ lookup('config', application_id, 'services.oauth2.origin.host') }}
```

```jinja
upstreams = {{ lookup('config', application_id, 'services.oauth2.origin.host') }}  {# nocheck: lookup-config-path #}
```

`hardcoded-dns-resolver`, on the line that emits the literal IP, when the substitution point cannot consume `NETWORK_PUBLIC_DNS_RESOLVERS` (e.g. a CoreDNS `forward` directive in a non-Jinja template):

```text
forward . 1.1.1.1 8.8.8.8  # nocheck: hardcoded-dns-resolver
```

## Adding a new rule 🆕

1. Pick a kebab-case `<rule>` identifier.
2. Decide which position semantic from the list above fits the check.
3. Use the `is_suppressed_at` / `is_suppressed_in_head` / `is_suppressed_anywhere` helpers from [utils/annotations/suppress.py](../../../../utils/annotations/suppress.py) in your test. Do NOT roll a new regex.
4. Add the rule to the catalog table on this page.
