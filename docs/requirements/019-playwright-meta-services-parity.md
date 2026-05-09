# 019 - Playwright meta/services.yml parity coverage

## User Story

As a contributor maintaining the per-role Playwright suite, I want
every shared-service dependency a role declares in its
`meta/services.yml` to surface as a `<SERVICE>_SERVICE_ENABLED` flag
in `templates/playwright.env.j2` AND be consumed by at least one
gated scenario in `files/playwright.spec.js` — for every role, for
every service — so that a deploy with `SERVICES_DISABLED=<svc>`
deterministically reports the affected scenarios as `skipped` and a
deploy with the service enabled deterministically exercises the
integration. No silently undeclared dep, no flag without a consumer,
no spec scenario reading `process.env.<SVC>_SERVICE_ENABLED` outside
the helper.

## Context

[006 - Service-gated Playwright tests](006-playwright-service-gated-tests.md)
established the registry and the helper API:
`templates/playwright.env.j2` IS the per-role registry; a
`<SERVICE>_SERVICE_ENABLED` flag declared there is the contract that
authorises the spec to gate on `<service>`. Two integration tests
enforce both halves of the round-trip:

- [test_playwright_env_services_match.py](../../tests/integration/roles/test_playwright_env_services_match.py)
  (Test A): every entry in `meta/services.yml` with an `enabled:`
  key MUST appear as `<NAME>_SERVICE_ENABLED=` in the env template,
  unless marked `# nocheck: playwright-service-flag` on the
  services-yml entry.
- [test_playwright_spec_env_gates.py](../../tests/integration/roles/test_playwright_spec_env_gates.py)
  (Test B): every `<NAME>_SERVICE_ENABLED=` line in the env template
  MUST be consumed by at least one
  `requireService` / `skipUnlessServiceEnabled` /
  `isServiceEnabled` / `isServiceDisabledReason` call in the spec,
  unless marked `# nocheck: playwright-service-gate` on the env
  line.

Today most roles fail Test A: their `meta/services.yml` declares a
broad shared-service dep set (`dashboard`, `oidc`, `ldap`, `email`,
`matomo`, `logout`, `oauth2`, `prometheus`, …) but the env template
ships only a subset, and the spec gates only a subset of that
subset. Two earlier requirements close specific slices of this gap:
[017 - Playwright biber RBAC coverage](017-playwright-biber-rbac-coverage.md)
covers the RBAC dimension and
[018 - Playwright LDAP authentication coverage](018-playwright-ldap-coverage.md)
covers the LDAP-vs-OIDC variant split. This requirement closes the
remaining global parity gap between `meta/services.yml`,
`templates/playwright.env.j2`, and `files/playwright.spec.js` — for
every service the role declares, not just the ones already covered
by 017 / 018.

The trigger for this requirement was the dashboard tile: every
`web-app-*` role declares `dashboard:` in its services.yml because
the canonical user entry point is "open the dashboard, click the
role's card". Today no role's playwright env carries the
`DASHBOARD_SERVICE_ENABLED` flag and no spec exercises the tile
click. The dashboard tile is therefore the recurring example
throughout this document, but the policy is symmetric across every
shared service the role depends on.

## Acceptance Criteria

### Policy

- [ ] **Test A parity (services.yml → env).** For every role with
  `templates/playwright.env.j2`, every top-level entry in
  `meta/services.yml` that carries an `enabled:` key MUST either
  surface as `<NAME>_SERVICE_ENABLED=` in the env template (with
  `<NAME>` being the upper-snake form of the service key per
  `service-gating.js::envKey`), or carry a
  `# nocheck: playwright-service-flag` marker on the comment block
  immediately above the services-yml key with a one-line rationale.
  No silent omission.
- [ ] **Test B parity (env → spec).** For every role with both an
  env template and a spec, every `<NAME>_SERVICE_ENABLED=` line in
  the env template MUST be referenced by at least one helper call
  (`requireService` / `skipUnlessServiceEnabled` /
  `isServiceEnabled` / `isServiceDisabledReason`) in the spec, or
  carry a `# nocheck: playwright-service-gate` marker on the env
  line itself with a one-line rationale.
- [ ] **No bypass.** Specs MUST NOT read
  `<NAME>_SERVICE_ENABLED` directly via `process.env`. All reads go
  through the helper from
  [roles/test-e2e-playwright/files/service-gating.js](../../roles/test-e2e-playwright/files/service-gating.js).
  This is the same rule from
  [006](006-playwright-service-gated-tests.md) and is verified by
  the `process.env\.[A-Z_]*_SERVICE_ENABLED` grep in the
  verification block below.
- [ ] **Variant separation.** A scenario that gates on multiple
  services MUST gate on each via a separate
  `skipUnlessServiceEnabled('<svc>')` call. Combining unrelated
  services in one body is forbidden — the matrix-deploy variants
  exist to drive each branch in isolation, and bundling them
  defeats the variant matrix (same rule as
  [018](018-playwright-ldap-coverage.md)).

### Per-service scenario shapes

The following table is the recurring catalogue of "what counts as
exercising the service" when a role gates a scenario on it. The
list is non-exhaustive; new services inherit the same contract
shape (a real end-to-end flow that fails when the integration
breaks, gated via `skipUnlessServiceEnabled`).

| Service | Scenario shape |
| --- | --- |
| `dashboard` | Open `${DASHBOARD_BASE_URL}/`, locate the role's tile via `a[href*="<canonical>"]`, assert presence + correct `href`, click, assert landing on `CANONICAL_DOMAIN`. Reference: [web-app-kix/files/playwright.spec.js](../../roles/web-app-kix/files/playwright.spec.js). |
| `oidc` | Visit a protected URL, assert redirect to Keycloak's `openid-connect/auth`, perform the login, assert redirect back, assert authenticated UI. |
| `ldap` | LDAP-bind path per [018](018-playwright-ldap-coverage.md). MUST exercise both the admin and the canonical non-admin user `biber` per [017](017-playwright-biber-rbac-coverage.md). |
| `oauth2` | oauth2-proxy gates the role's UI: assert a request to a protected path triggers the proxy, completes through Keycloak, lands back, and `/oauth2/sign_out` re-engages the gate. |
| `email` | Send mail in / receive mail out via the role's mail surface (where applicable). For roles that only originate notifications, verify the rendered body via the test mailbox. |
| `logout` | Universal-logout endpoint clears the role's session AND the SSO session, the next protected request re-engages auth. |
| `matomo` | The Matomo tracking snippet for `application_id` is present in the role's HTML, and a navigation generates the expected `/matomo.php` request. |
| `prometheus` | The role exposes its `/metrics` endpoint at the documented path AND Prometheus reports the role's target as `up=1` (where the spec runs against a deployed Prometheus). |
| `discourse` | Per [007 - WordPress → Discourse round-trip](007-wordpress-discourse-post-round-trip.md) and analogous role-pair flows. |
| `simpleicons`, `cdn`, `css`, `javascript`, `asset` | Static-asset deps. The scenario asserts the role's HTML references the expected asset host AND a request returns < 400 with the right content-type. |
| `redis`, `mariadb`, `postgres` | Database-engine deps. NOT independently gateable from a Playwright surface in most roles; mark with `# nocheck: playwright-service-flag` and rely on the role's own integration tests. The exception is roles that surface DB health in the UI. |
| `coturn`, `collabora`, `onlyoffice`, `talk`, `greenlight`, `ollama`, `webmail`, `webdav`, `imap`, `smtp`, `antispam`, `antivirus`, `oletools`, `fetchmail`, `front`, `resolver`, `admin`, `worker`, `view`, `web` | Sub-component deps. Either a real scenario where the component is the surface of the integration, OR `# nocheck: playwright-service-flag` with a rationale pointing at the role-local test that does cover it. |
| `<role-name itself>` (`mailu`, `friendica`, `pixelfed`, `discourse`, `keycloak`, `libretranslate`, `simpleicons`, `cdn`, …) | Self-provider entries. MUST be marked `# nocheck: playwright-service-flag` per [006](006-playwright-service-gated-tests.md)'s "MUST NOT self-gate" rule. |

### Self-gate exceptions

Roles whose `meta/services.yml` declares the service they themselves
provide MUST mark that entry with
`# nocheck: playwright-service-flag`. The catalogue from
[006](006-playwright-service-gated-tests.md):

- [ ] [web-app-keycloak](../../roles/web-app-keycloak/) — IS the
  OIDC provider; MUST NOT gate on `oidc`.
- [ ] [web-app-mailu](../../roles/web-app-mailu/) — IS the mail
  provider; MUST NOT gate on `email` / `mailu`.
- [ ] [web-app-matomo](../../roles/web-app-matomo/) — IS the
  analytics provider; MUST NOT gate on `matomo`.
- [ ] [web-app-dashboard](../../roles/web-app-dashboard/) — IS the
  dashboard; MUST NOT gate on `dashboard`.
- [ ] [web-app-discourse](../../roles/web-app-discourse/) — IS
  Discourse; MUST NOT gate on `discourse`.
- [ ] [web-app-pixelfed](../../roles/web-app-pixelfed/) — IS
  Pixelfed; MUST NOT gate on `pixelfed`.
- [ ] [web-app-friendica](../../roles/web-app-friendica/) — IS
  Friendica; MUST NOT gate on `friendica`.
- [ ] [web-app-prometheus](../../roles/web-app-prometheus/) — IS
  Prometheus; MUST NOT gate on `prometheus`.
- [ ] [web-svc-cdn](../../roles/web-svc-cdn/) — IS the CDN; MUST
  NOT gate on `cdn`.
- [ ] [web-svc-libretranslate](../../roles/web-svc-libretranslate/)
  — IS LibreTranslate; MUST NOT gate on `libretranslate`.
- [ ] [web-svc-simpleicons](../../roles/web-svc-simpleicons/) —
  IS the SimpleIcons service; MUST NOT gate on `simpleicons`.

The same rule applies to any future role whose primary entity is
also referenced in its own `meta/services.yml`.

### Out-of-scope entries

Roles that have a `meta/services.yml` entry for a shared dep but
legitimately have no Playwright-reachable surface for it MUST mark
the entry with `# nocheck: playwright-service-flag` and document
the reason in `README.md`. Typical reasons:

- Role has no Playwright spec yet (then **every** services.yml
  entry's flag rendering is deferred until the spec exists; do not
  pre-render flags that nothing consumes).
- Service is consumer-side only with no UI surface (e.g. a backend
  worker queue used by a daemon).
- Service is a pure infrastructure dep covered by its own spec
  (e.g. `redis`, `mariadb`, `postgres` engines for most roles).

### Per-role status matrix

Snapshot at the moment this requirement opened. Each row records
the per-role state of the parity contract: does the role ship an
env template / a spec, and which `meta/services.yml` entries are
**still missing** as `<NAME>_SERVICE_ENABLED=` flags in the env
template (Test A drift). The list IS the work that needs to happen
to close this requirement for the role: each missing service MUST
be either rendered as a flag (and gated in the spec), dropped from
`meta/services.yml` if it is no longer consumed, or marked
`# nocheck: playwright-service-flag` with a rationale.

Test B drift (env flag without spec gate) is currently empty across
the tree — the eight earlier offenders were closed by deleting
unused flags. The column is omitted from the matrix below until a
new Test B drift entry appears; new offenders surface immediately
in the test output.

Legend: ✅ present, ❌ missing, — not applicable (no env / no spec).
Service entries annotated `*(self-gate)*` are role-self-provider
entries that MUST be closed via `# nocheck:
playwright-service-flag` per the section above.

| Rolle | hat env | hat spec | fehlende `<NAME>_SERVICE_ENABLED=` Flags (Test A) |
| --- | --- | --- | --- |
| `web-app-akaunting` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `mariadb`, `matomo`, `oauth2`, `prometheus`, `redis` |
| `web-app-baserow` | ✅ | ✅ | `css`, `dashboard`, `email`, `javascript`, `logout`, `matomo`, `oauth2`, `postgres`, `prometheus`, `redis` |
| `web-app-bigbluebutton` | ✅ | ✅ | `collabora`, `coturn`, `css`, `dashboard`, `email`, `greenlight`, `ldap`, `logout`, `matomo`, `oidc`, `postgres`, `prometheus` |
| `web-app-bluesky` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `matomo`, `oauth2`, `prometheus`, `view`, `web` |
| `web-app-bookwyrm` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `matomo`, `oauth2`, `postgres`, `prometheus`, `redis`, `worker` |
| `web-app-bridgy-fed` | ✅ | ✅ | `css`, `dashboard`, `logout`, `matomo`, `oauth2`, `oidc`, `prometheus` |
| `web-app-chess` | ❌ | ❌ | — |
| `web-app-confluence` | ❌ | ❌ | — |
| `web-app-dashboard` | ✅ | ✅ | `asset`, `cdn`, `css`, `dashboard` *(self-gate)*, `javascript`, `logout`, `matomo`, `oidc`, `prometheus`, `simpleicons` |
| `web-app-decidim` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `matomo`, `oauth2`, `oidc`, `postgres`, `prometheus`, `redis` |
| `web-app-discourse` | ✅ | ✅ | `asset`, `css`, `dashboard`, `discourse` *(self-gate)*, `email`, `ldap`, `logout`, `matomo`, `oidc`, `postgres`, `prometheus`, `redis` |
| `web-app-espocrm` | ❌ | ❌ | — |
| `web-app-fediwall` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `matomo`, `oauth2`, `oidc`, `prometheus` |
| `web-app-fider` | ✅ | ✅ | `css`, `dashboard`, `email`, `javascript`, `logout`, `matomo`, `oauth2`, `oidc`, `postgres`, `prometheus`, `redis` |
| `web-app-flowise` | ✅ | ✅ | `css`, `dashboard`, `email`, `javascript`, `logout`, `matomo`, `oauth2`, `ollama`, `prometheus`, `redis` |
| `web-app-friendica` | ✅ | ✅ | `css`, `dashboard`, `email`, `friendica` *(self-gate)*, `ldap`, `logout`, `mariadb`, `matomo`, `oauth2`, `oidc`, `prometheus` |
| `web-app-funkwhale` | ❌ | ❌ | — |
| `web-app-fusiondirectory` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `matomo`, `oauth2`, `prometheus` |
| `web-app-gitea` | ✅ | ✅ | `css`, `dashboard`, `email`, `ldap`, `logout`, `mariadb`, `matomo`, `oauth2`, `oidc`, `prometheus`, `redis` |
| `web-app-gitlab` | ❌ | ❌ | — |
| `web-app-hugo` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `matomo`, `oauth2`, `oidc`, `prometheus` |
| `web-app-jenkins` | ✅ | ✅ | `css`, `dashboard`, `logout`, `matomo`, `prometheus` |
| `web-app-jira` | ❌ | ❌ | — |
| `web-app-joomla` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `mariadb`, `matomo`, `prometheus` |
| `web-app-keycloak` | ✅ | ✅ | `css`, `dashboard`, `email`, `keycloak` *(self-gate)*, `ldap`, `logout`, `matomo`, `postgres`, `prometheus`, `recaptcha` |
| `web-app-kix` | ✅ | ✅ | `css`, `dashboard`, `email`, `ldap`, `logout`, `matomo`, `oauth2`, `prometheus`, `redis` |
| `web-app-lam` | ❌ | ❌ | — |
| `web-app-listmonk` | ❌ | ❌ | — |
| `web-app-littlejs` | ❌ | ❌ | — |
| `web-app-magento` | ❌ | ❌ | — |
| `web-app-mailu` | ✅ | ✅ | `admin`, `antispam`, `antivirus`, `css`, `dashboard`, `fetchmail`, `front`, `imap`, `logout`, `mailu` *(self-gate)*, `mariadb`, `matomo`, `oidc`, `oletools`, `prometheus`, `redis`, `resolver`, `smtp`, `webdav`, `webmail` |
| `web-app-mastodon` | ❌ | ❌ | — |
| `web-app-matomo` | ✅ | ✅ | `css`, `dashboard`, `logout`, `mariadb`, `matomo` *(self-gate)*, `oauth2`, `oidc`, `prometheus`, `redis` |
| `web-app-matrix` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `matomo`, `oidc`, `postgres`, `prometheus` |
| `web-app-mattermost` | ✅ | ✅ | `css`, `dashboard`, `email`, `javascript`, `ldap`, `logout`, `matomo`, `oauth2`, `oidc`, `postgres`, `prometheus`, `redis` |
| `web-app-mediawiki` | ❌ | ❌ | — |
| `web-app-mig` | ✅ | ✅ | `css`, `dashboard`, `logout`, `matomo`, `oauth2`, `oidc`, `prometheus`, `redis` |
| `web-app-mini-qr` | ❌ | ❌ | — |
| `web-app-minio` | ✅ | ✅ | `css`, `dashboard`, `javascript`, `logout`, `matomo`, `ollama`, `prometheus`, `redis` |
| `web-app-mobilizon` | ❌ | ❌ | — |
| `web-app-moodle` | ✅ | ✅ | `css`, `dashboard`, `email`, `ldap`, `logout`, `mariadb`, `matomo`, `oidc`, `prometheus` |
| `web-app-navigator` | ❌ | ❌ | — |
| `web-app-nextcloud` | ✅ | ✅ | `collabora`, `coturn`, `css`, `dashboard`, `email`, `hcaptcha`, `ldap`, `logout`, `mariadb`, `matomo`, `oidc`, `onlyoffice`, `prometheus`, `redis`, `talk` |
| `web-app-oauth2-proxy` | ❌ | ❌ | — |
| `web-app-odoo` | ✅ | ✅ | `css`, `dashboard`, `email`, `javascript`, `ldap`, `logout`, `matomo`, `oidc`, `postgres`, `prometheus`, `redis` |
| `web-app-opencloud` | ✅ | ✅ | `css`, `dashboard`, `email`, `ldap`, `logout`, `matomo`, `oidc`, `prometheus` |
| `web-app-openproject` | ❌ | ❌ | — |
| `web-app-opentalk` | ✅ | ✅ | `coturn`, `css`, `dashboard`, `email`, `ldap`, `logout`, `matomo`, `oidc`, `postgres`, `prometheus`, `redis` |
| `web-app-openwebui` | ✅ | ✅ | `css`, `dashboard`, `email`, `javascript`, `ldap`, `logout`, `matomo`, `oidc`, `ollama`, `prometheus`, `redis` |
| `web-app-peertube` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `matomo`, `oidc`, `postgres`, `prometheus`, `redis` |
| `web-app-pgadmin` | ❌ | ❌ | — |
| `web-app-phpldapadmin` | ❌ | ❌ | — |
| `web-app-phpmyadmin` | ❌ | ❌ | — |
| `web-app-pixelfed` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `mariadb`, `matomo`, `oidc`, `pixelfed` *(self-gate)*, `prometheus`, `redis` |
| `web-app-postmarks` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `matomo`, `oauth2`, `prometheus` |
| `web-app-pretix` | ❌ | ❌ | — |
| `web-app-prometheus` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `matomo`, `oauth2`, `oidc`, `prometheus` *(self-gate)* |
| `web-app-roulette-wheel` | ❌ | ❌ | — |
| `web-app-shopware` | ❌ | ❌ | — |
| `web-app-snipe-it` | ❌ | ❌ | — |
| `web-app-socialhome` | ❌ | ❌ | — |
| `web-app-sphinx` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `matomo`, `oauth2`, `oidc`, `prometheus` |
| `web-app-suitecrm` | ❌ | ❌ | — |
| `web-app-taiga` | ✅ | ✅ | `css`, `dashboard`, `email`, `javascript`, `ldap`, `logout`, `matomo`, `oauth2`, `oidc`, `postgres`, `prometheus` |
| `web-app-wordpress` | ✅ | ✅ | `css`, `dashboard`, `logout`, `mariadb`, `matomo`, `prometheus` |
| `web-app-xwiki` | ❌ | ❌ | — |
| `web-app-yourls` | ✅ | ✅ | `css`, `dashboard`, `email`, `logout`, `mariadb`, `matomo`, `oauth2`, `prometheus` |
| `web-svc-cdn` | ✅ | ✅ | `cdn` *(self-gate)*, `css`, `dashboard`, `javascript`, `matomo`, `prometheus` |
| `web-svc-libretranslate` | ✅ | ✅ | `css`, `dashboard`, `javascript`, `libretranslate` *(self-gate)*, `logout`, `matomo`, `oauth2`, `prometheus`, `recaptcha`, `redis` |
| `web-svc-simpleicons` | ✅ | ✅ | `css`, `dashboard`, `matomo`, `oauth2`, `prometheus`, `recaptcha`, `redis`, `simpleicons` *(self-gate)* |
| `web-svc-xmpp` | ✅ | ✅ | `logout`, `oidc`, `prometheus` |

#### How to read the matrix

- **Each entry in the "fehlende Flags" column** is a Test A failure
  the requirement closes by either:
  1. **Adding the flag.** Render
     `<NAME>_SERVICE_ENABLED={{ … }}` into
     `templates/playwright.env.j2` per the value-shape rules from
     [006](006-playwright-service-gated-tests.md), AND add a
     `skipUnlessServiceEnabled('<svc>')`-gated scenario to
     `files/playwright.spec.js` per the per-service catalogue
     above. **This is the default.**
  2. **Dropping the entry.** Remove the service from
     `meta/services.yml` if the role no longer consumes it. Verify
     [test_services_explicit.py](../../tests/integration/roles/meta/services/run_after/test_services_explicit.py)
     stays green.
  3. **Marking it.** Place `# nocheck: playwright-service-flag`
     in the comment block immediately above the services-yml key
     with a one-line rationale. Use only for documented
     exceptions: self-gate (see "Self-gate exceptions" above),
     infrastructural / non-Playwright-reachable surfaces, or roles
     that legitimately have no spec for the surface.
- **Self-gate entries** (annotated `*(self-gate)*` in the matrix)
  MUST be closed via path 3 (`# nocheck`).
  [006](006-playwright-service-gated-tests.md) forbids self-gating;
  rendering the flag for the role's own provider service would
  contradict that rule.
- **Rows with `hat env ❌` / `hat spec ❌`**: roles that have not
  yet adopted Playwright. The matrix does not enumerate their
  per-service drift because Test A only fires when both
  `templates/playwright.env.j2` and `meta/services.yml` exist.
  When such a role grows a Playwright spec, the new env template
  MUST satisfy this requirement from day one — never as a follow-up.
- **`web-app-mailu` is the largest single row** (20 missing flags)
  because its `meta/services.yml` declares every Mailu sub-component
  (`admin`, `imap`, `smtp`, `antispam`, …) as a service entry. The
  expected closure path for Mailu is: render flags for the
  shared-dep entries (`oidc`, `dashboard`, `matomo`, `logout`,
  `prometheus`); `# nocheck: playwright-service-flag` every internal
  sub-component (`admin`, `antispam`, …) plus the self-gate
  `mailu` per [006](006-playwright-service-gated-tests.md).

### Closure shape per matrix row

For each non-self-gate, non-empty row in the matrix, the closing
contributor MUST produce:

1. The new `<NAME>_SERVICE_ENABLED=…` lines in
   `templates/playwright.env.j2`. Value shape per
   [006](006-playwright-service-gated-tests.md): a Jinja expression
   resolving to literal `"true"` / `"false"`.
2. The new gated scenario(s) in `files/playwright.spec.js`. The
   spec MUST `require('./service-gating')` at the top and call
   `skipUnlessServiceEnabled('<svc>')` at the start of each
   service-dependent scenario body.
3. A `README.md` paragraph (or a sentence in the existing
   "Playwright" section) listing which shared services the spec now
   exercises, so a contributor planning a reduced deploy can
   predict which scenarios will skip.

### Verification

- [ ] [test_playwright_env_services_match.py](../../tests/integration/roles/test_playwright_env_services_match.py)
  MUST be green for the in-scope tree at the close of this
  requirement.
- [ ] [test_playwright_spec_env_gates.py](../../tests/integration/roles/test_playwright_spec_env_gates.py)
  MUST be green for the in-scope tree at the close of this
  requirement.
- [ ] [test_playwright_env_keys_used.py](../../tests/lint/ansible/roles/test_playwright_env_keys_used.py)
  MUST stay green throughout the rollout. A new env key without a
  spec consumer is a regression even when both new tests above are
  passing on their respective slices.
- [ ] A run with `SERVICES_DISABLED=<svc>` MUST report every
  scenario gated on `<svc>` as
  `skipped: <NAME>_SERVICE_ENABLED=false`, never `failed`. The
  verification MUST cover at least one representative entry from
  each non-trivial column of the per-service catalogue
  (`dashboard`, `oidc`, `ldap`, `email`, `logout`, `matomo`).
- [ ] A run without `SERVICES_DISABLED` MUST produce at least one
  `passed` scenario per (role, service) combination that is in
  scope per the matrix above. An empty-skip pass (zero scenarios
  executed for a service across the whole suite) MUST fail the
  verification step.
- [ ] A grep `process.env\.[A-Z_]*_SERVICE_ENABLED` over the spec
  tree (excluding
  [roles/test-e2e-playwright/files/service-gating.js](../../roles/test-e2e-playwright/files/service-gating.js))
  MUST return zero hits, proving every spec routes its gates
  through the helper.

## See Also

- [006 - Service-gated Playwright tests](006-playwright-service-gated-tests.md)
- [017 - Playwright biber RBAC coverage](017-playwright-biber-rbac-coverage.md)
- [018 - Playwright LDAP authentication coverage](018-playwright-ldap-coverage.md)
- [test_playwright_env_services_match.py](../../tests/integration/roles/test_playwright_env_services_match.py)
- [test_playwright_spec_env_gates.py](../../tests/integration/roles/test_playwright_spec_env_gates.py)
- [test_playwright_env_keys_used.py](../../tests/lint/ansible/roles/test_playwright_env_keys_used.py)
