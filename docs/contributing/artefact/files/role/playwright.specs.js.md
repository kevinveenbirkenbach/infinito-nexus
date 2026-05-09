# `playwright.spec.js` 🎭

This page describes what every role's `roles/<role>/files/playwright.spec.js` MUST contain: file placement, the two persona flows, per-service assertions, technical rules, and final-state guarantees.

For framework and runner mechanics see [Playwright Tests](../../../actions/testing/playwright.md).
For the authoring procedure see [Agent `playwright.spec.js`](../../../../agents/files/role/playwright.spec.js.md).
For the env contract see [Agent `playwright.env.j2`](../../../../agents/files/role/playwright.env.j2.md).

## File placement 📁

- The spec MUST be at `roles/<role>/files/playwright.spec.js`.
- `playwright.config.js` and `package.json` are central, NOT per-role. See [Playwright Tests → Role-Local Files](../../../actions/testing/playwright.md#role-local-files-).

## Two personas, fixed flow 🚶

Every spec ships exactly **two scenarios**, one per persona.
Both exist in the deploy fixture: `administrator` (admin) and `biber` (non-admin).
The flow shape is identical across roles; only the role-specific selectors and the post-login assertion change.
Service-dependent steps MUST be guarded with [`skipUnlessServiceEnabled('<svc>')`](../../../../../roles/test-e2e-playwright/files/service-gating.js) so a deploy with `SERVICES_DISABLED=<svc>` reports the affected step as `skipped: <NAME>_SERVICE_ENABLED=false`, never `failed`.

### `biber`: single-app journey

```
[ ${DASHBOARD_BASE_URL}/ ]              skipUnlessServiceEnabled('dashboard')
        │  click role tile  (a[href*="<canonical>"])
        ▼
[ ${APP_BASE_URL}/ ]                    skipUnlessServiceEnabled('oidc' | 'oauth2' | 'ldap')
        │  Keycloak login (biber)
        ▼
[ authenticated app ]                   assert: user-visible authenticated element
        │  click universal logout / GET ${LOGOUT_URL}
        ▼
[ unauthenticated landing ]             assert: protected request re-engages auth
```

### `administrator`: multi-app round-trip

```
[ ${DASHBOARD_BASE_URL}/ ]              skipUnlessServiceEnabled('dashboard')
        │  click Prometheus tile        skipUnlessServiceEnabled('prometheus')
        ▼
[ ${PROMETHEUS_BASE_URL}/ ]
        │  assert: role's target up=1
        │  back-nav to dashboard
        ▼
[ ${DASHBOARD_BASE_URL}/ ]
        │  click role tile
        ▼
[ ${APP_BASE_URL}/ ]                    skipUnlessServiceEnabled('oidc' | 'oauth2' | 'ldap')
        │  Keycloak login (administrator)
        ▼
[ authenticated app ]                   assert: admin-visible element
                                        (admin panel, management menu, ...)
        │  click universal logout / GET ${LOGOUT_URL}
        ▼
[ unauthenticated landing ]             assert: protected request re-engages auth
```

### Test-body template

```js
const { test, expect } = require("@playwright/test");
const { skipUnlessServiceEnabled } = require("./service-gating");

test("biber: dashboard → app → logout", async ({ page }) => {
  skipUnlessServiceEnabled("dashboard");
  // (add gates for the role's auth chain)
  // 1. dashboard → click role tile
  // 2. complete role-specific auth chain as biber
  // 3. assert authenticated user-visible element
  // 4. universal logout
  // 5. assert unauthenticated landing
});

test("administrator: dashboard → prometheus → dashboard → app → logout", async ({ page }) => {
  skipUnlessServiceEnabled("dashboard");
  // 1. dashboard
  // 2. (gated on 'prometheus') prometheus tile → assert role target up=1
  // 3. back to dashboard
  // 4. role tile → admin auth chain
  // 5. assert admin-visible element
  // 6. universal logout
  // 7. assert unauthenticated landing
});
```

### Invariants (every spec, every role)

- Both personas always start at `${DASHBOARD_BASE_URL}/`.
- The role tile is always located by `a[href*="<canonical>"]`, never by a brittle role-name string.
- Both personas always end on a verified unauthenticated landing via the universal-logout endpoint.
- The admin always inserts the Prometheus health check between dashboard and app under test.
  Future admin-only health-check surfaces follow the same pattern: visit, assert health, back-nav, continue.
- Every service-dependent step uses `skipUnlessServiceEnabled(...)`.
  Direct `process.env` reads of `<NAME>_SERVICE_ENABLED` are forbidden.
- Baseline scenarios (reachability, CSP, canonical-domain DOM assertion, logged-out final state) MUST NOT gate on any service.
  A deploy with every shared service disabled MUST still leave a passing baseline suite.

## Per-service assertion catalogue 🚦

What "exercise the service" means at each gate inside the persona flows.
Non-exhaustive; new services inherit the same shape (real end-to-end check that fails when the integration breaks, gated via `skipUnlessServiceEnabled`).

| Service | Assertion at the gate |
| --- | --- |
| `dashboard` | Open `${DASHBOARD_BASE_URL}/`, locate role tile via `a[href*="<canonical>"]`, assert presence + correct `href`, click, assert landing on `CANONICAL_DOMAIN`. |
| `oidc` | Visit protected URL, assert redirect to Keycloak's `openid-connect/auth`, log in, assert redirect back, assert authenticated UI. |
| `ldap` | LDAP-bind path. MUST exercise admin AND `biber`. |
| `oauth2` | Protected path triggers oauth2-proxy → Keycloak → callback; `/oauth2/sign_out` re-engages the gate. |
| `email` | Send / receive via the role's mail surface, OR verify rendered notification body via the test mailbox. |
| `logout` | Universal-logout endpoint clears role + SSO session; next protected request re-engages auth. |
| `matomo` | Tracking snippet for `application_id` is in the HTML; navigation generates the expected `/matomo.php` request. |
| `prometheus` | `/metrics` reachable at the documented path; Prometheus reports the role's target as `up=1`. |
| `discourse` | WordPress to Discourse post round-trip and analogous role-pair flows. |
| Static assets (`simpleicons`, `cdn`, `css`, `javascript`, `asset`) | The role's HTML references the expected asset host AND a request returns < 400 with the right content-type. |
| DB engines (`redis`, `mariadb`, `postgres`) | Default: `# nocheck: playwright-service-flag`. Covered by role-local integration tests. Exception: roles that surface DB health in the UI. |
| Sub-components (`coturn`, `collabora`, `onlyoffice`, `talk`, `greenlight`, `ollama`, `webmail`, `webdav`, `imap`, `smtp`, `antispam`, `antivirus`, `oletools`, `fetchmail`, `front`, `resolver`, `admin`, `worker`, `view`, `web`) | Real scenario where the component is the surface, OR `# nocheck: playwright-service-flag` with a pointer to the role-local test that covers it. |
| `<role-name itself>` | Self-provider entries. MUST be `# nocheck: playwright-service-flag` per the "no self-gate" rule. |

## Triggers: when to add or update a scenario ✍️

- Whenever role-local `style.css` or `javascript.js` changes user-visible behaviour, the spec MUST assert on the visible effect.
- Whenever the role enables an auth integration (OIDC, oauth2, LDAP), at least one persona's flow MUST exercise the integrated login path (not only a local-form login).
- When the application supports peer-to-peer messaging, the spec MUST cover a bi-directional `biber` ↔ `administrator` exchange (each delivery asserted in the recipient's inbox from an isolated browser context).
- Existing scenarios MUST NOT be deleted when "optimising" a spec.
  Rewrite them to satisfy the rules above or strengthen assertions; do not shrink coverage.
  Deletions are only acceptable when the underlying behaviour was removed from the role itself.

## Selectors and waits ⏳

- Selectors MUST prefer accessible roles, form-scoped buttons, and other stable hooks over brittle DOM lookups or generic labels that can match unrelated UI (e.g. topbar search vs. login submit).
- Waits MUST target meaningful page state (visible elements, URL changes, attached locators).
  Fixed sleeps MUST NOT be used where an explicit wait is available.
- When a flow runs inside an iframe and login or OIDC clicks can reload it, the spec MUST treat the reload as a navigation event: await the next visible state or the new iframe URL, then reacquire the frame and rebuild locators before the next interaction.
  A stale iframe handle MUST NOT be reused across redirects.

## Environment contract 🔌

- Every env variable the spec reads MUST be exposed in the role's `templates/playwright.env.j2`.
  Names MUST match exactly.
- URLs, domains, and credentials MUST come from the rendered `.env`.
  No hardcoded values in the spec.

## Service gating contract 🔒

- All `<NAME>_SERVICE_ENABLED` reads go through the `service-gating.js` helper, never `process.env` directly.
- The helper hard-fails on unknown service names.
  Adding a new gate requires both the env-template flag and at least one `skipUnlessServiceEnabled('<svc>')` call in the spec; the parity guards [test_playwright_env_services_match.py](../../../../../tests/integration/roles/test_playwright_env_services_match.py) and [test_playwright_spec_env_gates.py](../../../../../tests/integration/roles/test_playwright_spec_env_gates.py) enforce that contract.

## Final state ✅

- Every scenario MUST end with the browser in a clearly logged-out state.
- The browser console MUST be clean of errors when the flow depends on injected JavaScript.
