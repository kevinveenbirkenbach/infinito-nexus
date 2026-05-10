# 019 - Playwright meta/services.yml parity coverage

## Vision

The unit of coverage is the role's single `files/playwright.spec.js`.
That one file MAY contain any number of `test()` blocks, but for every `(role, included-service)` pair there MUST be at least one gated step or scenario inside the file that:

1. **runs** when the service is enabled, and
2. **skips cleanly** (`skipped: <NAME>_SERVICE_ENABLED=false`) when the service is disabled, never `failed`.

A service "included" means a top-level entry in `roles/<role>/meta/services.yml`.
Skip-on-disabled is enforced through the shared [service-gating.js](../../roles/test-e2e-playwright/files/service-gating.js) helper from [006](006-playwright-service-gated-tests.md).

The user-journey shape every `web-app-*` spec MUST instantiate is defined in [playwright.specs.js.md](../contributing/artefact/files/role/playwright.specs.js.md): one `guest` scenario, one `biber` scenario, and one `administrator` scenario, named `<persona>: <flow>`.
**All three persona scenarios MUST exist in every `web-app-*` role's spec under this requirement; their presence is part of the acceptance criteria, not optional polish.**

The Playwright spec file IS the single point of truth for the persona contract.
When the SPOT spec contract page and a role's spec disagree, the spec wins; documentation MUST be brought into alignment, not the other way around.

`web-svc-*` roles are auth-less by construction (no end-user UI, programmatic API only).
They are NOT subject to the persona contract; their spec ships a single baseline reachability scenario plus the per-service gates that apply to them.
The persona-collapse exception in [playwright.specs.js.md](../contributing/artefact/files/role/playwright.specs.js.md) covers this case.

The acceptance criteria below are the mechanical translation of this contract.

## Rules

| # | Rule | Enforced by |
| --- | --- | --- |
| 1 | Every entry in `meta/services.yml` with an `enabled:` key MUST surface as `<NAME>_SERVICE_ENABLED=` in `templates/playwright.env.j2`, OR carry `# nocheck: playwright-service-flag` above the key with a one-line rationale. **Globally exempt: `dashboard` and `prometheus`.** Their per-consumer reachability is owned by the provider's own spec via `*_TARGET_ROLES_JSON` (see Rule 13); `web-app-*` consumers still declare the service in `meta/services.yml` for inventory completeness but do NOT render the `<NAME>_SERVICE_ENABLED=` flag. **For `dashboard` only:** a non-`web-app-*` role MUST NOT declare the service with a truthy `enabled`/`shared` flag (literal `true` or the `'<role>' in group_names` Jinja form); the dashboard tile grid is reserved for end-user-visible web-app surfaces and infrastructural roles never contribute a tile. Non-`web-app-*` roles that need a static no-tile declaration MAY ship `dashboard: { enabled: false, shared: false }`, otherwise the entry MUST be dropped. | [test_playwright_env_services_match.py](../../tests/integration/roles/test_playwright_env_services_match.py) (Test A); for the dashboard-scope sub-rule: [test_dashboard_integration_scope.py](../../tests/integration/roles/test_dashboard_integration_scope.py) |
| 2 | Every `<NAME>_SERVICE_ENABLED=` line in the env template MUST be consumed by ≥1 `requireService` / `skipUnlessServiceEnabled` / `isServiceEnabled` / `isServiceDisabledReason` call in `files/playwright.spec.js`, OR carry `# nocheck: playwright-service-gate` on the env line. | [test_playwright_spec_env_gates.py](../../tests/integration/roles/test_playwright_spec_env_gates.py) (Test B) |
| 3 | Every `web-app-*` role's `files/playwright.spec.js` MUST contain the three persona scenarios defined in [playwright.specs.js.md](../contributing/artefact/files/role/playwright.specs.js.md), named `guest: <flow>`, `biber: <flow>`, and `administrator: <flow>` respectively. Each persona enters the role's own canonical surface directly (no dashboard tile click); the auth chain runs through OAuth2-Proxy + Keycloak regardless of how the user arrived. The guest scenario MUST assert the unauthenticated visitor never reaches the role's authenticated surface. **Cross-service probes (biber denied at prometheus / matomo, administrator accepted at prometheus / matomo, dashboard tile reachability) are NOT part of the per-role persona; they are owned by the provider's own spec per Rule 13.** `web-svc-*` roles and `web-app-*` roles whose upstream has no auth surface (federation-only or static-only, see the auth-less list under [Iteration order](#iteration-order)) MAY collapse all three into a single baseline scenario. | [test_naming.py](../../tests/lint/ansible/roles/web-app/playwright/persona/test_naming.py) enforces the `<persona>: <flow>` shape across all `web-app-*` roles; [test_required_envs.py](../../tests/lint/ansible/roles/web-app/playwright/persona/test_required_envs.py) enforces the auth-less collapse exception consistency. The persona-naming lint is the role-closure gate for the matrix below. |
| 4 | Specs MUST NOT read `<NAME>_SERVICE_ENABLED` directly via `process.env`. All reads go through the helper. | grep verification (see below) |
| 5 | A scenario that depends on multiple services MUST gate each via a separate `skipUnlessServiceEnabled('<svc>')` call. No bundled multi-service gates; bundling defeats the variant matrix (same rule as [018](018-playwright-ldap-coverage.md)). | review |
| 6 | A new env key without a spec consumer is a regression. | [test_env_keys_used.py](../../tests/lint/ansible/roles/web-app/playwright/test_env_keys_used.py) |
| 7 | Every persona scenario AND every contract test in `files/playwright.spec.js` MUST simulate a real user flow with at least one `expect(...)` / `await <fn>(...)` / equivalent assertion. Stub bodies (`TODO`, `STUB`, `FIXME`, empty, or only `skipUnlessServiceEnabled`) are FORBIDDEN. The rollout's intent is real flows that fail when the integration breaks; a passing-by-default body provides no signal. | [test_no_stub_tests.py](../../tests/lint/ansible/roles/web-app/playwright/test_no_stub_tests.py) |
| 8 | Tests MUST drive user-initiated actions through the rendered UI (click on logout button / link / menu, click on submit button, …) and MUST NOT short-circuit them with `page.goto(<action-endpoint>)`. The logout step in particular MUST click the role's own in-app logout control on the currently authenticated surface (or open a user / account menu first when the control is nested). When the universal-logout service is attached, its injected JavaScript auto-rewrites the click target to redirect through Keycloak's end-session endpoint, so the test does NOT branch on whether universal-logout is active. Navigating directly to `${LOGOUT_URL}` is forbidden. | review (this requirement) |
| 9 | Every persona scenario MUST drive a real, role-specific interaction after the auth chain settles (or directly on the role surface when no auth is required). The `biber` interaction MUST exercise a regular end-user action; the `administrator` interaction MUST exercise an admin-only surface. Specs pass the interaction in via `runBiberFlow(page, { biberInteraction })` / `runAdminFlow(page, { adminInteraction })`. No generic default exists — a generic "click any link" assertion tests nothing role-specific. | review (this requirement) |
| 10 | When the role supports peer-to-peer interaction (messaging, comment threads, federation round-trips, calendar invites, …), the spec MUST include a separate `biber ↔ administrator: <flow>` test that opens two browser contexts, drives the round-trip end-to-end, and asserts both sides see the expected payload. The shared `runPeerExchangeFlow(browser, { peerExchange })` helper provides the two-context scaffolding. Roles whose upstream offers no peer interaction surface MUST NOT add the test. | review (this requirement) |
| 11 | Persona scenarios MUST FAIL LOUDLY when the persona cannot execute the contracted journey, never silently `test.skip(...)` on runtime detection of "no logout button" / "no authenticated surface" / "no admin UI marker". A silent skip hides real regressions (broken OIDC mapping, removed logout button, misconfigured oauth2-proxy, drifted UI selectors) behind a green deploy. The ONLY clean-skip mechanism is an EXPLICIT env opt-out declared by the role: `PERSONA_BIBER_BLOCKED=true` / `PERSONA_ADMINISTRATOR_BLOCKED=true` / `PERSONA_GUEST_BLOCKED=true` rendered in `templates/playwright.env.j2`, with a documented rationale in the role's README or TODO. Without the flag the persona helper hard-fails the test. | [test_strict_mode.py](../../tests/lint/ansible/roles/web-app/playwright/persona/test_strict_mode.py) (`test_persona_skips_only_via_explicit_opt_out`) + persona-helper bodies in `roles/test-e2e-playwright/files/personas/{biber,admin,guest}.js` |
| 12 | Direct-probe deny-checks at prometheus / matomo MUST validate the response body, not only the status code. A `200 OK` is acceptable ONLY when the body contains role-specific markers proving the response is the genuine provider surface (e.g. `prometheus_build_info`, `<title>Prometheus</title>` for prometheus; matomo's login-form markers / `piwik` or `matomo` for matomo). Any 200 with a non-matching body is treated as a misconfigured proxy or a denial-as-200 surface and fails loudly. | [test_strict_mode.py](../../tests/lint/ansible/roles/web-app/playwright/persona/test_strict_mode.py) (`test_deny_helpers_validate_body_on_200`) + bodies in `roles/web-app-prometheus/files/playwright.spec.js` and `roles/web-app-matomo/files/playwright.spec.js` (per Rule 13: provider-owned SPOT) |
| 13 | **SPOT-owned cross-service assertions.** Dashboard tile reachability, prometheus scrape parity, and matomo tracker presence are owned by the provider's own spec, not duplicated across consumer roles. Each provider's `templates/playwright.env.j2` renders a `<NAME>_TARGET_ROLES_JSON` manifest via the `lookup('roles_with_service', '<svc>')` Ansible lookup ([plugins/lookup/roles_with_service.py](../../plugins/lookup/roles_with_service.py)), enumerating every role whose merged applications config declares the service with both `enabled` and `shared` truthy and whose role exposes a canonical domain. The provider's `files/playwright.spec.js` parameterises one assertion per consumer over that manifest. The shared persona helpers (`runBiberFlow`, `runAdminFlow`) consequently no longer drive cross-service probes — they exercise the role under test only. | provider specs `roles/web-app-{dashboard,prometheus,matomo}/files/playwright.spec.js` and the `roles_with_service` lookup |

## Per-service scenario catalogue

The per-service assertion catalogue (what each gate's body MUST exercise: `dashboard` tile click, `oidc` round-trip, `ldap` bind, `email` send/receive, `prometheus` `up=1`, …) is documented in [playwright.specs.js.md](../contributing/artefact/files/role/playwright.specs.js.md#per-service-assertion-catalogue-).
The persona flow is the surrounding journey; the catalogue tells the spec what to assert at each gate inside that journey.
This requirement's matrix below uses the catalogue's vocabulary but does not duplicate it; refer to that page for the per-service contract.

## Self-gate `# nocheck` list

The role IS the provider; the service entry MUST be marked
`# nocheck: playwright-service-flag`:

- [ ] `web-app-keycloak` → `oidc`
- [ ] `web-app-mailu` → `email`, `mailu`
- [ ] `web-app-matomo` → `matomo`
- [ ] `web-app-dashboard` → `dashboard`
- [ ] `web-app-discourse` → `discourse`
- [ ] `web-app-pixelfed` → `pixelfed`
- [ ] `web-app-friendica` → `friendica`
- [ ] `web-app-prometheus` → `prometheus`
- [ ] `web-svc-cdn` → `cdn`
- [ ] `web-svc-libretranslate` → `libretranslate`
- [ ] `web-svc-simpleicons` → `simpleicons`

## Closure paths per matrix row

Each missing flag in the matrix is closed by exactly one of:

1. **Render flag + add gated scenario** *(default)*. Render `<NAME>_SERVICE_ENABLED={{ … }}` in `templates/playwright.env.j2` (literal `"true"` / `"false"` per [006](006-playwright-service-gated-tests.md)). Add a `skipUnlessServiceEnabled('<svc>')`-gated step inside the appropriate persona scenario in `files/playwright.spec.js` per [playwright.specs.js.md](../contributing/artefact/files/role/playwright.specs.js.md). Mention the service in the role's README so reduced-deploy skip behaviour is predictable.
2. **Drop the entry**. Remove the service from `meta/services.yml` if no longer consumed. Verify [test_services_explicit.py](../../tests/integration/roles/meta/services/run_after/test_services_explicit.py) stays green.
3. **`# nocheck: playwright-service-flag`**. Comment block above the services-yml key with a one-line rationale. Reserved for self-gate, infrastructural, or no-Playwright-surface cases.

**Dashboard-scope exception (non-`web-app-*` roles).** Paths 1 and 3 are NOT available for a `dashboard:` block in any `web-svc-*` / `sys-*` / `desk-*` / `drv-*` role; [test_dashboard_integration_scope.py](../../tests/integration/roles/test_dashboard_integration_scope.py) forbids every truthy `dashboard.{enabled,shared}` declaration outside `web-app-*`.
For these roles, closure runs exclusively through path 2 (drop the entry) OR through a static `dashboard: { enabled: false, shared: false }` declaration when the inventory-side registry visibility is required.
Persona scenarios are already covered by the auth-less collapse, so removing the `dashboard:` block does NOT shrink coverage.

Closure of any row also requires that the role's spec already contains the two persona scenarios (Rule 3); a row's missing flag MAY be added inside a new persona scenario, but the row is NOT closed until both persona scenarios exist.

## Per-role drift matrix

Snapshot at requirement-open. Test B drift is currently empty; the column is omitted until a new offender appears.
Each non-empty row in the "fehlende Flags" column is the work for that role.
Closing a role's row also requires the role's spec to ship the two persona scenarios (Rule 3); a role with `hat spec ✅` and a non-empty drift list MUST add the missing gates **inside** those persona bodies, not as ungated standalone tests.

Legend: ✅ present, ❌ missing, — n/a (no env / no spec).
`*(self-gate)*` = MUST be closed via `# nocheck: playwright-service-flag` (path 3 above).

| Rolle | hat env | hat spec | fehlende `<NAME>_SERVICE_ENABLED=` Flags (Test A) |
| --- | --- | --- | --- |
| ~~`web-app-akaunting`~~ | ✅ | ✅ | ~~`css`, `dashboard`, `email`, `logout`, `mariadb`, `matomo`, `oauth2`, `prometheus`, `redis`~~ — role-closed (Playwright green; biber and administrator personas explicit-skipped via `PERSONA_BIBER_BLOCKED=true` and `PERSONA_ADMINISTRATOR_BLOCKED=true` in env, rationale: OIDC auto-provisioning not wired, tracked in role TODO.md) |
| ~~`web-app-baserow`~~ | ✅ | ✅ | ~~`css`, `dashboard`, `email`, `javascript`, `logout`, `matomo`, `oauth2`, `postgres`, `prometheus`, `redis`~~ — role-closed |
| `web-app-bigbluebutton` | ✅ | ✅ | `collabora`, `coturn`, `css`, `dashboard`, `email`, `greenlight`, `ldap`, `logout`, `matomo`, `oidc`, `postgres`, `prometheus` |
| ~~`web-app-bluesky`~~ | ✅ | ✅ | ~~`css`, `dashboard`, `email`, `logout`, `matomo`, `oauth2`, `prometheus`, `view`, `web`~~ — role-closed (Playwright green; biber+admin personas explicit-skipped via PERSONA_<X>_BLOCKED, social-app mobile SPA has logout in profile menu unreachable to auth-surface check; bespoke OIDC + LDAP variant tests verify both personas authenticate via the broker) |
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
| ~~`web-app-keycloak`~~ | ✅ | ✅ | ~~`css`, `dashboard`, `email`, `keycloak` *(self-gate)*, `ldap`, `logout`, `matomo`, `postgres`, `prometheus`, `recaptcha`~~ — role-closed (auth-provider exception: generic persona scenarios are exempt; bespoke "master-realm super administrator", "normal-realm administrator", "normal-realm biber" tests cover the persona contract via the realm account UI) |
| `web-app-kix` | ✅ | ✅ | `css`, `dashboard`, `email`, `ldap`, `logout`, `matomo`, `oauth2`, `prometheus`, `redis` |
| `web-app-lam` | ❌ | ❌ | — |
| `web-app-listmonk` | ❌ | ❌ | — |
| `web-app-littlejs` | ❌ | ❌ | — |
| `web-app-magento` | ❌ | ❌ | — |
| `web-app-mailu` | ✅ | ✅ | `admin`, `antispam`, `antivirus`, `css`, `dashboard`, `fetchmail`, `front`, `imap`, `logout`, `mailu` *(self-gate)*, `mariadb`, `matomo`, `oidc`, `oletools`, `prometheus`, `redis`, `resolver`, `smtp`, `webdav`, `webmail` |
| `web-app-mastodon` | ❌ | ❌ | — |
| ~~`web-app-matomo`~~ | ✅ | ✅ | ~~`css`, `dashboard`, `logout`, `mariadb`, `matomo` *(self-gate)*, `oauth2`, `oidc`, `prometheus`, `redis`~~ — role-closed (Playwright green; admin-only role: personas skip via `safeSkipUnlessEnabled("dashboard")` because `services.dashboard.enabled: false` in services.yml — bespoke "matomo administrator" test covers the admin journey) |
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
| ~~`web-app-prometheus`~~ | ✅ | ✅ | ~~`css`, `dashboard`, `email`, `logout`, `matomo`, `oauth2`, `oidc`, `prometheus` *(self-gate)*~~ — role-closed (Playwright green; admin-only role: personas skip via `safeSkipUnlessEnabled("dashboard")` because `services.dashboard.enabled: false` — bespoke `metricz`, `dashboard-to-prometheus admin SSO`, and `biber-denied-access` tests cover the contract) |
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
| `web-svc-cdn` | ✅ | ✅ | `cdn` *(self-gate)*, `css`, `javascript`, `matomo`, `prometheus` |
| `web-svc-libretranslate` | ✅ | ✅ | `css`, `javascript`, `libretranslate` *(self-gate)*, `logout`, `matomo`, `oauth2`, `prometheus`, `recaptcha`, `redis` |
| `web-svc-simpleicons` | ✅ | ✅ | `css`, `matomo`, `oauth2`, `prometheus`, `recaptcha`, `redis`, `simpleicons` *(self-gate)* |
| `web-svc-xmpp` | ✅ | ✅ | `logout`, `oidc`, `prometheus` |

Rows with both `❌` are roles without Playwright artefacts yet.
When they grow a spec, the new env template MUST satisfy this requirement from day one AND the new spec MUST ship both persona scenarios per Rule 3.

## Closure procedure

The agent MUST follow this procedure verbatim to close the matrix above.

### Required reading

Load all of the following before the first deploy.

1. [Contributing `playwright.spec.js`](../contributing/artefact/files/role/playwright.specs.js.md): the persona scenarios, invariants, per-service catalogue, env contract, and final state.
2. [Role Loop](../agents/action/iteration/role.md): per-role deploy procedure, certificate trust, inspect-before-redeploy, matrix-variant mechanics.
3. [Playwright Spec Loop](../agents/action/iteration/playwright.md): inner-loop edits against an already-running stack.

### Autonomy

- The agent MUST run the rollout autonomously without questions back to the operator.
- The agent MUST NOT ask "should I disable matomo/email" or any other deploy-time question; this rollout deploys with NO `SERVICES_DISABLED`.
- The agent MUST fix every failure that is caused by or related to this rollout (env-template drift, missing gates, persona scenarios, pattern-transfer regressions, …) without asking.
- Failures clearly unrelated to the rollout (an upstream image outage, a flaky network test in another module, a pre-existing CI flake on a path this rollout does not touch) MUST be ignored: the agent does NOT deep-dive into them.
  The agent SHOULD note the unrelated failure in the role's TODO.md if one exists, otherwise continue.
- The agent MUST NOT use any command that requires elevated permissions or an interactive approval prompt.
  Allowed permissions are defined by [.claude/settings.json](../../.claude/settings.json); commands that fall under `ask` or `deny` MUST NOT be invoked.
- Matrix-variant roles MUST be iterated through every declared variant; the role-closure gate (see below) only fires when every variant passes.
  Variants are read from `roles/<role>/meta/variants.yml` and driven via `VARIANT=<idx>` per [Role Loop → Matrix variants](../agents/action/iteration/role.md#matrix-variants).

### Closure vocabulary

This requirement uses two distinct closure terms; do NOT mix them.

- **Flag closure** is the per-row event in the matrix below: a single `<NAME>_SERVICE_ENABLED=` flag has been rendered, gated, dropped, or `# nocheck`-marked per the [Closure paths](#closure-paths-per-matrix-row).
  Closing a flag is a code change; it does NOT require a deploy on its own.
- **Role closure** is the per-role event: every flag for the role is closed AND the role's spec ships the persona scenarios (where applicable) AND the role's full-cycle deploy plus Playwright spec passed for every declared variant AND Tests A and B are green for the role.

The matrix tracks flag closure; the iteration tracks role closure.

### Per-role flow

For each role in the [Iteration order](#iteration-order) below:

1. Run `make test`.
   On failure, fix the underlying issue if it is rollout-related; per [Autonomy](#autonomy), unrelated failures are ignored.
2. Run `make deploy-fresh-purged-apps APPS=<role> FULL_CYCLE=true` to establish a fresh full-cycle baseline WITHOUT `SERVICES_DISABLED`.
   For matrix-variant roles, iterate through every variant declared in `roles/<role>/meta/variants.yml` via `VARIANT=<idx>` per [Role Loop → Matrix variants](../agents/action/iteration/role.md#matrix-variants); the role is NOT role-closed until every variant has produced a passing deploy plus passing Playwright spec.
3. If the deploy fails or the spec fails, follow [Role Loop](../agents/action/iteration/role.md) and [Playwright Spec Loop](../agents/action/iteration/playwright.md) to fix the root cause.
   Apply the fix in the repository files (NOT in the staged copy or the running container).
4. If a specific service genuinely cannot work for the role (upstream limitation, infrastructural exclusion, scope conflict), perform a **flag closure** through one of the closure paths above: either disable the service in `roles/<role>/meta/services.yml` (when the role legitimately has no business consuming it), or mark the entry with `# nocheck: playwright-service-flag` and document the rationale in a one-line comment above the key (e.g. `# nocheck: playwright-service-flag — self-provider`, `# nocheck: playwright-service-flag — infrastructural, no Playwright surface`, `# nocheck: playwright-service-flag — covered by tests/integration/services/test_<x>.py`, `# nocheck: playwright-service-flag — upstream offers no <svc> integration`).
   The agent decides which path applies based on the role's documented contract; it does NOT ask the operator.
5. The role's `roles/<role>/meta/variants.yml` MAY need adjustment when its declared variants do not exercise the service combinations the spec gates on.
   The agent MUST edit `meta/variants.yml` whenever any of the following holds:
   - A new variant is required to exercise a service-off path that the matrix does not yet cover (e.g. an LDAP-only variant pinning `oidc.enabled: false` plus `ldap.enabled: true` per [018](018-playwright-ldap-coverage.md), or a variant that disables `matomo` to validate the skip-on-disabled contract).
   - An existing variant pins service flags that conflict with the spec's gates (e.g. the variant pins `oauth2.enabled: true` while the role's spec only ever drives the `oidc` path); fix the variant to match what the spec actually exercises.
   - A variant references a service key that is no longer declared in `meta/services.yml`; remove the override.
   Variants edits MUST keep [test_auth_coverage.py](../../tests/integration/roles/meta/variants/test_auth_coverage.py) and [test_services_match.py](../../tests/integration/roles/meta/variants/test_services_match.py) green; the agent re-runs both after every `meta/variants.yml` change.
   Variants edits are part of the same role-closure scope and do NOT trigger a separate commit.
6. The role is **role-closed** only when:
   - the final `make deploy-fresh-purged-apps APPS=<role> FULL_CYCLE=true` run completed successfully for every variant, AND
   - the Playwright spec passed for every variant, AND
   - the role's `files/playwright.spec.js` ships the three persona scenarios per [Rule 3](#rules) (or the auth-less single-scenario collapse for `web-svc-*` and the auth-less `web-app-*` exceptions), AND
   - both [test_playwright_env_services_match.py](../../tests/integration/roles/test_playwright_env_services_match.py) and [test_playwright_spec_env_gates.py](../../tests/integration/roles/test_playwright_spec_env_gates.py) are green for the role, AND
   - if `meta/variants.yml` was edited, [test_auth_coverage.py](../../tests/integration/roles/meta/variants/test_auth_coverage.py) and [test_services_match.py](../../tests/integration/roles/meta/variants/test_services_match.py) are green.
7. **Strike the role through in the matrix** as the progress marker (see [Resumability](#resumability)) and move to the next role.

### Pattern transfer

After a role role-closes successfully, the agent MUST extract the **learnings** from that role and apply them to every later role in the iteration order **before** running the next role's deploy.
Pattern transfer is a code-edit step, not a deploy step: each receiving role still goes through its own [Per-role flow](#per-role-flow) when its turn comes; the deploy never spans more than one role at a time.

Learnings to propagate include every per-service assertion shape from the [per-service assertion catalogue](../contributing/artefact/files/role/playwright.specs.js.md#per-service-assertion-catalogue-):

- the `dashboard` tile-click flow (locate role tile via `a[href*="<canonical>"]`, click, assert canonical landing);
- the `prometheus` interface check for the administrator (`up=1` for the role's target on `/api/v1/query?query=up`);
- the `prometheus` deny-check for biber (admin-only surface MUST refuse the biber identity);
- the `matomo` admin-login for the administrator (lands on the matomo admin UI from the dashboard tile);
- the `matomo` deny-check for biber (admin-only surface MUST refuse the biber identity);
- the CSP injection assertion (every persona; the page's `Content-Security-Policy` header MUST list every enabled injector host);
- the `guest` denial flow (unauthenticated visitor never reaches an authenticated surface; empty-credentials submission MUST be rejected by the IdP);
- the `oidc` Keycloak round-trip (redirect to `openid-connect/auth`, login, redirect back, authenticated assertion);
- the `oauth2` proxy-gate flow;
- the `logout` universal-logout assertion;
- the `matomo` tracking snippet check;
- the `ldap` bind path (admin AND `biber`);
- the `email`, `discourse`, federation, and any other service-pair flow.

For every receiving role, the agent MUST adapt the propagated pattern to the role-specific selectors and credentials.
Receiving roles whose `meta/services.yml` does NOT declare the relevant service MUST be skipped from that particular pattern transfer.
The transfer happens **immediately** after the source role closes successfully; deferral to a later pass is forbidden.

### Preserving existing tests

The rollout is purely additive.
The agent MUST NOT delete, shorten, or weaken any working test code in `files/playwright.spec.js`.
The persona scenarios and per-service gates land **alongside** the existing scenarios, never instead of them.

Specifically:

- A passing scenario MUST stay passing through the rollout.
  If a refactor risks breaking it, the agent MUST split the change so the existing scenario keeps its current shape and the new persona / gated scenarios are added next to it.
- Existing helper functions, selectors, and `test.beforeEach` setup MUST be preserved; new scenarios SHOULD reuse them rather than introducing parallel copies.
- An existing scenario MAY be **renamed** to follow the `<persona>: <flow>` naming convention from [Rule 3](#rules) when it already drives the persona's flow end-to-end; renaming MUST NOT change the assertions or the gated services.
- Deletion of an existing scenario is only allowed when the underlying behaviour has been removed from the role itself (the same exception that already lives in the [trigger conditions](../contributing/artefact/files/role/playwright.specs.js.md#triggers-when-to-add-or-update-a-scenario-) of `playwright.specs.js.md`).
  In every other case the agent MUST extend, not replace.

### Iteration order

Sorted by [`infinito meta roles applications complexity`](../../cli/meta/roles/applications/complexity/__main__.py) (ascending; lowest complexity first).
**Within a tier, the order is dependency-aware**, not alphabetical: providers go before consumers, even when the complexity score is identical, because consumers' persona scenarios authenticate against / route through the providers.
The list snapshot is the agent's starting plan.

#### Tier 12 (providers and shared services)

In dependency order:

1. `web-svc-asset`, `web-svc-cdn`, `web-svc-file`, `web-svc-logout`, `web-svc-simpleicons` — base providers with no shared-service dependencies (auth-less; persona scenarios do NOT apply).
2. `web-app-keycloak` — OIDC/LDAP provider; depends only on its own postgres backend.
3. `web-app-dashboard` — consumes Keycloak OIDC; the canonical user entry point that every later persona scenario starts from.
4. `web-app-mailu`, `web-app-matomo`, `web-app-prometheus` — provider apps that consume Keycloak (OIDC) and the dashboard (tile + canonical landing).

#### Tier 13 (single-tier consumers)

Within Tier 13 the iteration order is alphabetical because every entry consumes the providers above and has no further intra-tier ordering constraint.

`web-app-akaunting`, `web-app-baserow`, `web-app-bluesky`, `web-app-bookwyrm`, `web-app-bridgy-fed`, `web-app-chess`, `web-app-confluence`, `web-app-decidim`, `web-app-discourse`, `web-app-espocrm`, `web-app-fider`, `web-app-friendica`, `web-app-funkwhale`, `web-app-fusiondirectory`, `web-app-gitea`, `web-app-gitlab`, `web-app-hugo`, `web-app-jenkins`, `web-app-jira`, `web-app-joomla`, `web-app-kix`, `web-app-lam`, `web-app-listmonk`, `web-app-littlejs`, `web-app-magento`, `web-app-mastodon`, `web-app-matrix`, `web-app-mattermost`, `web-app-mediawiki`, `web-app-mig`, `web-app-mini-qr`, `web-app-mobilizon`, `web-app-moodle`, `web-app-navigator`, `web-app-oauth2-proxy`, `web-app-odoo`, `web-app-opencloud`, `web-app-openproject`, `web-app-peertube`, `web-app-pgadmin`, `web-app-phpldapadmin`, `web-app-phpmyadmin`, `web-app-pixelfed`, `web-app-postmarks`, `web-app-pretix`, `web-app-roulette-wheel`, `web-app-shopware`, `web-app-snipe-it`, `web-app-socialhome`, `web-app-sphinx`, `web-app-suitecrm`, `web-app-taiga`, `web-app-xwiki`, `web-app-yourls`, `web-svc-collabora`, `web-svc-coturn`, `web-svc-html`, `web-svc-libretranslate`, `web-svc-onlyoffice`, `web-svc-xmpp`.

#### Tier 14

`web-app-flowise`, `web-app-minio`, `web-app-opentalk`, `web-app-openwebui`, `web-app-wordpress`, `web-svc-legal`.

#### Tier 15

`web-app-bigbluebutton`, `web-app-fediwall`.

#### Tier 16

`web-app-nextcloud`.

#### Auth-less roles (persona-collapse exception)

Per [Rule 3](#rules), the following roles MAY collapse the two persona scenarios into a single baseline reachability scenario because their upstream offers no auth surface (federation-only protocol, static-only output, programmatic-API-only service, internal sub-component of another role):

- Every `web-svc-*` role (no end-user UI by construction).
- `web-app-bridgy-fed` (federation-only; users authenticate at their source platform, not locally).
- `web-app-hugo` (static-site generator; no runtime auth).
- `web-app-littlejs`, `web-app-chess`, `web-app-mini-qr`, `web-app-roulette-wheel` (static / single-purpose toys; no upstream auth surface).
- `web-app-navigator`, `web-app-mig` (in-app modules of `web-app-dashboard`; no separate auth surface).
- `web-app-oauth2-proxy` (sidecar auth proxy; never directly user-facing).

Every other `web-app-*` role MUST ship both persona scenarios per Rule 3.

### Resumability

The rollout is long-running and MAY be interrupted (sandbox timeout, context exhaustion, machine restart).
The drift matrix above IS the progress marker; the agent does NOT maintain a separate state file.

When resuming, the agent MUST:

1. Re-derive the iteration order from `infinito meta roles applications complexity` to pick up any new roles added since the snapshot.
2. Re-run [test_playwright_env_services_match.py](../../tests/integration/roles/test_playwright_env_services_match.py) and [test_playwright_spec_env_gates.py](../../tests/integration/roles/test_playwright_spec_env_gates.py) to discover which roles are already role-closed (zero drift) and which are still open.
3. Pick the lowest-tier role that is NOT role-closed and resume the [Per-role flow](#per-role-flow) on it.
4. Replay [Pattern transfer](#pattern-transfer) for any patterns the agent had landed pre-interruption: re-read each role-closed role's spec to identify which catalogue entries it covers, then ensure those patterns are present in every later not-yet-closed role's spec before continuing.

The agent MUST NOT redo deploys for already-role-closed roles unless a later edit broke their tests.

### Commits

- The agent MUST NOT create intermediate commits during the rollout.
- The agent MUST stage incremental changes locally as it goes (so progress survives between roles) but MUST NOT commit until the final role in the iteration order has been role-closed.
- A single commit at the end of the rollout captures every change.
  The commit message format is not prescribed by this requirement; use a concise summary that mentions req 019.
- The agent MUST NOT push the final commit; the operator runs `git-sign-push` outside the sandbox.

## Verification

- [ ] Test A green tree-wide.
- [ ] Test B green tree-wide.
- [ ] [test_env_keys_used.py](../../tests/lint/ansible/roles/web-app/playwright/test_env_keys_used.py) green throughout the rollout.
- [ ] [test_no_stub_tests.py](../../tests/lint/ansible/roles/web-app/playwright/test_no_stub_tests.py) green tree-wide. Every persona scenario and every contract test drives a real user flow; no stub bodies survive.
- [ ] [test_naming.py](../../tests/lint/ansible/roles/web-app/playwright/persona/test_naming.py) green tree-wide. Every `web-app-*` role's `files/playwright.spec.js` contains a `guest: <flow>` test, a `biber: <flow>` test, AND an `administrator: <flow>` test (or the auth-less collapse exception, or an explicit `PERSONA_<X>_BLOCKED=true` opt-out per Rule 11).
- [ ] [test_required_envs.py](../../tests/lint/ansible/roles/web-app/playwright/persona/test_required_envs.py) green tree-wide. Roles that ship the auth-less collapse MUST be auth-less by construction (no `CANONICAL_DOMAIN` / `APP_BASE_URL`); any role pinning a persona-blocked flag MUST document the rationale in its README/TODO.
- [ ] [test_strict_mode.py](../../tests/lint/ansible/roles/web-app/playwright/persona/test_strict_mode.py) green tree-wide. Persona helpers fail loudly on un-executable journeys (Rule 11) and deny-check helpers validate the response body on a 200 (Rule 12).
- [ ] [test_dashboard_integration_scope.py](../../tests/integration/roles/test_dashboard_integration_scope.py) green tree-wide. No non-`web-app-*` role declares `dashboard:` with a truthy `enabled`/`shared` flag (Rule 1, dashboard-scope sub-rule).
- [ ] `SERVICES_DISABLED=<svc>` reports every gated scenario as `skipped: <NAME>_SERVICE_ENABLED=false`, never `failed`. MUST cover ≥1 scenario each for `dashboard`, `oidc`, `ldap`, `email`, `logout`, `matomo`.
- [ ] No-`SERVICES_DISABLED` run produces ≥1 `passed` scenario per in-scope `(role, service)` pair. Empty-skip = fail.
- [ ] `grep 'process.env\.[A-Z_]*_SERVICE_ENABLED'` over the spec tree (excluding `service-gating.js`) returns zero hits.
