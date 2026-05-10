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
| 3 | Every `web-app-*` role's `files/playwright.spec.js` MUST contain the three persona scenarios defined in [playwright.specs.js.md](../contributing/artefact/files/role/playwright.specs.js.md), named `guest: <flow>`, `biber: <flow>`, and `administrator: <flow>` respectively. Each persona enters the role's own canonical surface directly (no dashboard tile click); the auth chain runs through OAuth2-Proxy + Keycloak regardless of how the user arrived. The guest scenario MUST assert the unauthenticated visitor never reaches the role's authenticated surface. **Cross-service probes (biber denied at prometheus / matomo, administrator accepted at prometheus / matomo, dashboard tile reachability) are NOT part of the per-role persona; they are owned by the provider's own spec per Rule 13.** `web-svc-*` roles and `web-app-*` roles whose upstream has no auth surface (federation-only or static-only, see the auth-less list under [Iteration order](#iteration-order)) MAY collapse all three into a single baseline scenario. | [test_naming.py](../../tests/lint/ansible/roles/web-app/playwright/persona/test_naming.py) enforces the `<persona>: <flow>` shape across all `web-app-*` roles; [test_required_envs.py](../../tests/lint/ansible/roles/web-app/playwright/persona/test_required_envs.py) enforces the auth-less collapse exception consistency. The persona-naming lint is the role-closure gate for *spec shape*; the full role-closure definition (passing deploy, Test A, Test B, strict-mode lint) lives in [Closure vocabulary](#closure-vocabulary). |
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

## Closure paths per matrix row

When a future iteration surfaces fresh drift (a new `meta/services.yml` entry without a matching `<NAME>_SERVICE_ENABLED=` line, or a new matrix row that fails Test A), each missing flag is closed by exactly one of:

1. **Render flag + add gated scenario** *(default)*. Render `<NAME>_SERVICE_ENABLED={{ … }}` in `templates/playwright.env.j2` (literal `"true"` / `"false"` per [006](006-playwright-service-gated-tests.md)). Add a `skipUnlessServiceEnabled('<svc>')`-gated step inside the appropriate persona scenario in `files/playwright.spec.js` per [playwright.specs.js.md](../contributing/artefact/files/role/playwright.specs.js.md). Mention the service in the role's README so reduced-deploy skip behaviour is predictable.
2. **Drop the entry**. Remove the service from `meta/services.yml` if no longer consumed. Verify [test_services_explicit.py](../../tests/integration/roles/meta/services/run_after/test_services_explicit.py) stays green.
3. **`# nocheck: playwright-service-flag`**. Comment block above the services-yml key with a one-line rationale. Reserved for self-gate, infrastructural, or no-Playwright-surface cases.

**Dashboard-scope exception (non-`web-app-*` roles).** Paths 1 and 3 are NOT available for a `dashboard:` block in any `web-svc-*` / `sys-*` / `desk-*` / `drv-*` role; [test_dashboard_integration_scope.py](../../tests/integration/roles/test_dashboard_integration_scope.py) forbids every truthy `dashboard.{enabled,shared}` declaration outside `web-app-*`.
For these roles, closure runs exclusively through path 2 (drop the entry) OR through a static `dashboard: { enabled: false, shared: false }` declaration when the inventory-side registry visibility is required.
Persona scenarios are already covered by the auth-less collapse, so removing the `dashboard:` block does NOT shrink coverage.

Closure of any row also requires that the role's spec already contains the three persona scenarios (Rule 3); a row's missing flag MAY be added inside a new persona scenario, but the row is NOT closed until all three persona scenarios exist.

## Per-role iteration matrix

The matrix is sorted by `total` descending so the highest-coupling roles surface first; the agent walks the table top-to-bottom and treats `total` as the priority signal.
`total` is the sum of direct + transitive embeds and consumers per [`infinito meta roles applications complexity --sort total --order desc`](../../cli/meta/roles/applications/complexity/__main__.py).
Test A and Test B are currently green tree-wide, so no per-row drift list is carried in this table; the `notes` column captures role-specific contract context (auth-less collapse, persona blocked-flag opt-outs, bespoke admin-only test bodies).

Legend: ✅ present, ❌ missing.

| Role | total | has env | has spec | notes |
| --- | ---: | --- | --- | --- |
| `web-app-prometheus` | 173 | ✅ | ✅ | oauth2-proxy gates the role on `web-app-prometheus-administrator`; biber lacks the role so the proxy denies the session and biber has no in-app surface to drive a logout from — opt out via `PERSONA_BIBER_BLOCKED=true` (Rule 11). The administrator persona runs the standard oauth2-proxy → Keycloak chain. Bespoke `metricz`, `dashboard-to-prometheus admin SSO`, and `biber-denied-access` tests cover the SPOT-owned probes |
| `web-app-matomo` | 168 | ✅ | ✅ | admin-only role: persona stubs explicit-skipped via `PERSONA_BIBER_BLOCKED=true` / `PERSONA_ADMINISTRATOR_BLOCKED=true` in env (Rule 11); bespoke "matomo administrator" test covers the admin journey |
| `web-app-dashboard` | 162 | ✅ | ✅ |  |
| `web-svc-cdn` | 144 | ✅ | ✅ |  |
| `web-app-mailu` | 139 | ✅ | ✅ |  |
| `web-app-keycloak` | 130 | ✅ | ✅ | auth-provider exception: generic persona scenarios are exempt; bespoke "master-realm super administrator", "normal-realm administrator", "normal-realm biber" tests cover the persona contract via the realm account UI |
| `web-svc-simpleicons` | 92 | ✅ | ✅ |  |
| `web-app-nextcloud` | 27 | ✅ | ✅ |  |
| `web-app-discourse` | 24 | ✅ | ✅ |  |
| `web-app-bigbluebutton` | 24 | ✅ | ✅ |  |
| `web-app-opentalk` | 23 | ✅ | ✅ |  |
| `web-app-mastodon` | 23 | ❌ | ✅ |  |
| `web-app-friendica` | 23 | ✅ | ✅ |  |
| `web-app-openwebui` | 22 | ✅ | ✅ |  |
| `web-app-minio` | 22 | ✅ | ✅ |  |
| `web-app-listmonk` | 22 | ❌ | ✅ |  |
| `web-app-gitea` | 22 | ✅ | ✅ |  |
| `web-app-flowise` | 22 | ✅ | ✅ |  |
| `web-app-bookwyrm` | 22 | ✅ | ✅ |  |
| `web-app-xwiki` | 21 | ❌ | ✅ |  |
| `web-app-wordpress` | 21 | ✅ | ✅ |  |
| `web-app-taiga` | 21 | ✅ | ✅ |  |
| `web-app-shopware` | 21 | ❌ | ✅ |  |
| `web-app-pretix` | 21 | ❌ | ✅ |  |
| `web-app-odoo` | 21 | ✅ | ✅ |  |
| `web-app-moodle` | 21 | ✅ | ✅ |  |
| `web-app-mobilizon` | 21 | ❌ | ✅ |  |
| `web-app-mattermost` | 21 | ✅ | ✅ |  |
| `web-app-matrix` | 21 | ✅ | ✅ |  |
| `web-app-joomla` | 21 | ✅ | ✅ |  |
| `web-app-gitlab` | 21 | ❌ | ✅ |  |
| `web-app-fider` | 21 | ✅ | ✅ |  |
| `web-app-fediwall` | 21 | ✅ | ✅ |  |
| `web-app-espocrm` | 21 | ❌ | ✅ |  |
| `web-app-decidim` | 21 | ✅ | ✅ |  |
| `web-app-baserow` | 21 | ✅ | ✅ |  |
| `web-app-akaunting` | 21 | ✅ | ✅ | biber and administrator personas explicit-skipped via `PERSONA_BIBER_BLOCKED=true` and `PERSONA_ADMINISTRATOR_BLOCKED=true` in env; OIDC auto-provisioning not wired, see role TODO.md |
| `web-app-suitecrm` | 20 | ❌ | ✅ |  |
| `web-app-snipe-it` | 20 | ❌ | ✅ |  |
| `web-app-pixelfed` | 20 | ✅ | ✅ |  |
| `web-app-peertube` | 20 | ✅ | ✅ |  |
| `web-app-openproject` | 20 | ❌ | ✅ |  |
| `web-app-opencloud` | 20 | ✅ | ✅ |  |
| `web-app-mediawiki` | 20 | ❌ | ✅ |  |
| `web-app-jira` | 20 | ❌ | ✅ |  |
| `web-app-jenkins` | 20 | ✅ | ✅ |  |
| `web-app-fusiondirectory` | 20 | ✅ | ✅ |  |
| `web-app-funkwhale` | 20 | ❌ | ✅ |  |
| `web-app-confluence` | 20 | ❌ | ✅ |  |
| `web-app-bluesky` | 20 | ✅ | ✅ | biber and administrator personas explicit-skipped via `PERSONA_BIBER_BLOCKED=true` / `PERSONA_ADMINISTRATOR_BLOCKED=true`; the social-app mobile SPA hides the logout in a profile menu unreachable to the auth-surface check; bespoke OIDC + LDAP variant tests verify both personas authenticate via the broker |
| `web-app-yourls` | 19 | ✅ | ✅ |  |
| `web-app-phpldapadmin` | 19 | ❌ | ✅ |  |
| `web-app-pgadmin` | 19 | ❌ | ✅ |  |
| `web-app-magento` | 19 | ❌ | ✅ |  |
| `web-app-lam` | 19 | ❌ | ✅ |  |
| `web-app-kix` | 19 | ✅ | ✅ |  |
| `web-app-postmarks` | 18 | ✅ | ✅ |  |
| `web-app-phpmyadmin` | 18 | ❌ | ✅ |  |
| `web-app-chess` | 18 | ❌ | ✅ |  |
| `web-app-sphinx` | 17 | ✅ | ✅ |  |
| `web-app-roulette-wheel` | 17 | ❌ | ✅ |  |
| `web-app-oauth2-proxy` | 17 | ❌ | ✅ |  |
| `web-app-navigator` | 17 | ❌ | ✅ |  |
| `web-app-mini-qr` | 17 | ❌ | ✅ |  |
| `web-app-mig` | 17 | ✅ | ✅ |  |
| `web-app-littlejs` | 17 | ❌ | ✅ |  |
| `web-app-hugo` | 17 | ✅ | ✅ |  |
| `web-app-bridgy-fed` | 17 | ✅ | ✅ |  |
| `web-svc-xmpp` | 16 | ✅ | ✅ |  |
| `web-svc-libretranslate` | 16 | ✅ | ✅ |  |
| `web-app-socialhome` | 16 | ❌ | ✅ |  |

Rows with `has env ❌` and `has spec ✅` ship the auth-less collapse exception per Rule 3: the spec contains a single baseline reachability scenario and no env template is rendered because the role has no `<NAME>_SERVICE_ENABLED=` flags to gate on.
The matrix only lists roles that already ship a Playwright spec. A role with neither artefact is out of scope until it grows one; when that happens, the new spec MUST ship the three persona scenarios per Rule 3 (or document the auth-less collapse explicitly) AND the env template MUST satisfy this requirement from day one.

## Closure procedure

The agent MUST follow this procedure verbatim to walk every row of the matrix above through to role closure.

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

Learnings to propagate include every per-persona assertion shape from the [per-service assertion catalogue](../contributing/artefact/files/role/playwright.specs.js.md#per-service-assertion-catalogue-) that runs *inside the role under test*:

- the CSP injection assertion (every persona; the page's `Content-Security-Policy` header MUST list every enabled injector host);
- the `guest` denial flow (unauthenticated visitor never reaches an authenticated surface; empty-credentials submission MUST be rejected by the IdP);
- the `oidc` Keycloak round-trip (redirect to `openid-connect/auth`, login, redirect back, authenticated assertion);
- the `oauth2` proxy-gate flow;
- the `logout` universal-logout assertion;
- the `ldap` bind path (admin AND `biber`);
- the `email`, `discourse`, federation, and any other service-pair flow that the role itself initiates.

The SPOT-owned cross-service probes from Rule 13 are explicitly **out of scope** for pattern transfer — `dashboard` tile reachability, `prometheus` scrape parity (`up=1` per consumer), `matomo` tracker presence, and the per-consumer biber/administrator deny / accept checks at the prometheus and matomo admin surfaces all live in `roles/web-app-{dashboard,prometheus,matomo}/files/playwright.spec.js`, parameterised over `*_TARGET_ROLES_JSON`. Consumer specs MUST NOT carry these patterns.

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

The matrix above IS the iteration plan: rows are sorted by `total` descending, so the highest-priority role is the first row and the agent walks the table top-to-bottom.
`total` is the priority signal; ties are broken alphabetically by role name.
A hub fix propagates to the long tail of consumers via [Pattern transfer](#pattern-transfer), which is why the highest-`total` roles run first.
The agent MUST re-derive the table from [`infinito meta roles applications complexity --sort total --order desc`](../../cli/meta/roles/applications/complexity/__main__.py) on every resume per [Resumability](#resumability).

#### Auth-less roles (persona-collapse exception)

Per [Rule 3](#rules), the following roles MAY collapse the three persona scenarios into a single baseline reachability scenario because their upstream offers no auth surface (federation-only protocol, static-only output, programmatic-API-only service, internal sub-component of another role):

- Every `web-svc-*` role (no end-user UI by construction).
- `web-app-bridgy-fed` (federation-only; users authenticate at their source platform, not locally).
- `web-app-hugo` (static-site generator; no runtime auth).
- `web-app-littlejs`, `web-app-chess`, `web-app-mini-qr`, `web-app-roulette-wheel` (static / single-purpose toys; no upstream auth surface).
- `web-app-navigator`, `web-app-mig` (in-app modules of `web-app-dashboard`; no separate auth surface).
- `web-app-oauth2-proxy` (sidecar auth proxy; never directly user-facing).

Every other `web-app-*` role MUST ship all three persona scenarios per Rule 3.

### Resumability

The rollout is long-running and MAY be interrupted (sandbox timeout, context exhaustion, machine restart).
The iteration matrix above IS the progress marker; the agent strikes a row through (`~~`web-app-foo`~~`) after the role's full-cycle deploy plus Playwright spec pass for every declared variant, and does NOT maintain a separate state file.

When resuming, the agent MUST:

1. Re-derive the iteration order from `infinito meta roles applications complexity --sort total --order desc` to pick up any new roles added since the snapshot and to apply the highest-coupling-first walk per [Iteration order](#iteration-order).
2. Re-run [test_playwright_env_services_match.py](../../tests/integration/roles/test_playwright_env_services_match.py) and [test_playwright_spec_env_gates.py](../../tests/integration/roles/test_playwright_spec_env_gates.py) to discover which roles are already role-closed (zero drift) and which are still open.
3. Pick the highest-`total` role that is NOT role-closed and resume the [Per-role flow](#per-role-flow) on it.
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
- [ ] `SERVICES_DISABLED=<svc>` reports every gated scenario as `skipped: <NAME>_SERVICE_ENABLED=false`, never `failed`. MUST cover ≥1 scenario each for `oidc`, `ldap`, `email`, `logout`, `matomo`. The `dashboard` exemption (Rule 1) means consumers do not render `DASHBOARD_SERVICE_ENABLED=`; coverage for that service runs through web-app-dashboard's parameterised tile-reachability test (Rule 13).
- [ ] No-`SERVICES_DISABLED` run produces ≥1 `passed` scenario per in-scope `(role, service)` pair. Empty-skip = fail.
- [ ] `grep 'process.env\.[A-Z_]*_SERVICE_ENABLED'` over the spec tree (excluding `service-gating.js`) returns zero hits.
