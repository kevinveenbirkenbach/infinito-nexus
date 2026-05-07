const { test, expect } = require("@playwright/test");

test.use({ ignoreHTTPSErrors: true });

// -----------------------------------------------------------------------------
// Spec for web-app-moodle — covers both identity-integration variants:
//   variant 0 (default): auth_oidc + auth_ldap sync-only (hybrid)
//   variant 1:           auth_ldap only (no OIDC)
// See docs/requirements/015-moodle-self-built.md.
// -----------------------------------------------------------------------------

function decodeDotenvQuotedValue(value) {
  if (typeof value !== "string" || value.length < 2) return value;
  if (!(value.startsWith('"') && value.endsWith('"'))) return value;
  const encoded = value.slice(1, -1);
  try {
    return JSON.parse(`"${encoded}"`).replace(/\$\$/g, "$");
  } catch {
    return encoded.replace(/\$\$/g, "$");
  }
}
function normalizeBaseUrl(v) { return decodeDotenvQuotedValue(v || "").replace(/\/$/, ""); }
function installCspViolationObserver(page) {
  return page.addInitScript(() => {
    window.__cspViolations = [];
    window.addEventListener("securitypolicyviolation", (e) => {
      window.__cspViolations.push({ violatedDirective: e.violatedDirective, blockedURI: e.blockedURI });
    });
  });
}

const moodleBaseUrl   = normalizeBaseUrl(process.env.APP_BASE_URL);
const dashboardBaseUrl = normalizeBaseUrl(process.env.DASHBOARD_BASE_URL || "");
const oidcIssuerUrl   = normalizeBaseUrl(process.env.OIDC_ISSUER_URL || "");
const oidcClientId    = decodeDotenvQuotedValue(process.env.OIDC_CLIENT_ID || "");
const adminUsername   = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword   = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const biberUsername   = decodeDotenvQuotedValue(process.env.BIBER_USERNAME);
const biberPassword   = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD);
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN);

// Service-gating env flags per req-006.
const oidcEnabled = String(process.env.SERVICE_OIDC || "").toLowerCase() === "true";
const ldapEnabled = String(process.env.SERVICE_LDAP || "").toLowerCase() === "true";
const lamEnabled  = String(process.env.SERVICE_LAM  || "").toLowerCase() === "true";

const lamBaseUrl  = normalizeBaseUrl(process.env.LAM_BASE_URL || "");
const lamPassword = decodeDotenvQuotedValue(process.env.LAM_PASSWORD);


test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  expect(moodleBaseUrl, "APP_BASE_URL must be set").toBeTruthy();
  expect(adminUsername, "ADMIN_USERNAME must be set").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set").toBeTruthy();
  expect(biberUsername, "BIBER_USERNAME must be set").toBeTruthy();
  expect(biberPassword, "BIBER_PASSWORD must be set").toBeTruthy();
  await page.context().clearCookies();
  await installCspViolationObserver(page);
});

// ──────────────────────────────────────────────────────────────────────
// Baseline (both variants)
// ──────────────────────────────────────────────────────────────────────

test("moodle baseline: landing page reachable + canonical domain in URL", async ({ page }) => {
  const response = await page.goto(`${moodleBaseUrl}/`);
  expect(response, "expected response").toBeTruthy();
  expect(response.status(), "landing status < 400").toBeLessThan(400);
  expect(response.url().includes(canonicalDomain),
    `expected canonical domain "${canonicalDomain}" in url`).toBe(true);
});

test("moodle baseline: CSP header present, no violations on landing", async ({ page }) => {
  const response = await page.goto(`${moodleBaseUrl}/`);
  const csp = response.headers()["content-security-policy"];
  expect(csp, "Content-Security-Policy header expected").toBeTruthy();
  await page.waitForTimeout(500);
  const violations = await page.evaluate(() => window.__cspViolations || []);
  expect(violations, `unexpected CSP violations: ${JSON.stringify(violations)}`).toEqual([]);
});

// ──────────────────────────────────────────────────────────────────────
// Variant 0 — OIDC SSO (skipped when SERVICE_OIDC=false)
// ──────────────────────────────────────────────────────────────────────

// Variant 0 (OIDC hybrid) login flow is exercised end-to-end by the
// Moodle deploy itself (auth_oidc CLI config + auth_ldap sync) and by
// the Account REST + scope-discovery tests below. We deliberately do
// NOT drive Moodle's auth_oidc login redirect chain in Playwright —
// the Microsoft auth_oidc plugin uses Azure-AD-style parameters
// (resource=…, response_mode=form_post) whose end-to-end UI behavior
// is upstream territory and not introduced by req-015.

// ──────────────────────────────────────────────────────────────────────
// Variant 1 — auth_ldap primary (skipped when SERVICE_OIDC=true)
// ──────────────────────────────────────────────────────────────────────

test.describe("moodle LDAP-only (variant 1)", () => {
  test.skip(oidcEnabled, "OIDC shared service enabled — variant 1 not active");
  test.skip(!ldapEnabled, "LDAP shared service disabled");

  test("biber: direct LDAP-bind login via Moodle form", async ({ page }) => {
    await page.goto(`${moodleBaseUrl}/login/index.php`);
    // Variant 1: standard Moodle login form (no OIDC button).
    const usernameInput = page.locator("input[name='username'], input#username").first();
    await expect(usernameInput).toBeVisible({ timeout: 30_000 });
    await usernameInput.fill(biberUsername);
    await page.locator("input[name='password'], input#password").first().fill(biberPassword);
    await page.locator("button[type='submit'], input[type='submit'], #loginbtn").first().click();
    await page.waitForLoadState("load");
    const userMenu = page.locator(".usermenu, [data-region='user-menu-toggle'], a[href*='profile.php']").first();
    await expect(userMenu).toBeVisible({ timeout: 30_000 });
  });

  test("login page does NOT expose an OIDC entry point", async ({ page }) => {
    await page.goto(`${moodleBaseUrl}/login/index.php`);
    const oidcButton = page.locator("a, button").filter({
      hasText: /openid|oidc|keycloak|single.?sign.?on|sso/i
    }).first();
    expect(await oidcButton.count(), "OIDC button must NOT be visible in variant 1").toBe(0);
  });
});

// ──────────────────────────────────────────────────────────────────────
// Read-only enforcement (Moodle locks LDAP-backed fields)
// ──────────────────────────────────────────────────────────────────────

test.describe("moodle profile fields are read-only", () => {
  test.skip(!ldapEnabled, "LDAP shared service disabled");
  // Variant 0 hybrid login exercises a Microsoft-style OIDC redirect
  // chain that we do not drive in Playwright (see comment above the
  // OIDC variant 0 block). Variant 1 (LDAP-only) covers the same
  // field-lock semantics with the simple Moodle login form.
  test.skip(oidcEnabled, "covered by variant 1 LDAP-only run");

  test("biber profile-edit form locks all 19 Moodle profile-mapping fields", async ({ page }) => {
    await page.goto(`${moodleBaseUrl}/login/index.php`);
    await page.locator("input[name='username'], input#username").first().fill(biberUsername);
    await page.locator("input[name='password'], input#password").first().fill(biberPassword);
    await page.locator("button[type='submit'], input[type='submit'], #loginbtn").first().click();
    await page.waitForLoadState("load");

    // Open admin profile edit form.
    await page.goto(`${moodleBaseUrl}/user/edit.php`);
    await expect(page.locator("body")).toBeVisible({ timeout: 30_000 });

    // Per req-015 §"Profile-field mapping" — the 19 LDAP-backed Moodle
    // columns. All must be locked (readonly or disabled) by auth_ldap
    // when the field is present in the form.
    const moodleFields = [
      "firstname", "lastname", "middlename", "alternatename",
      "firstnamephonetic", "lastnamephonetic",
      "email", "phone1", "phone2",
      "address", "city", "country",
      "institution", "department", "description",
      "idnumber", "url", "lang", "timezone"
    ];
    for (const fieldName of moodleFields) {
      const input = page.locator(`input[name='${fieldName}'], select[name='${fieldName}'], textarea[name='${fieldName}']`).first();
      if (await input.count() > 0) {
        const readonly = await input.getAttribute("readonly");
        const disabled = await input.getAttribute("disabled");
        expect(
          readonly !== null || disabled !== null,
          `field "${fieldName}" must be readonly/disabled (LDAP-backed lock per req-015)`
        ).toBe(true);
      }
    }
  });
});

// ──────────────────────────────────────────────────────────────────────
// OIDC discovery — verify the keycloak realm exposes the moodle scope
// when MOODLE_OIDC_ENABLED (variant 0). Per req-015 §"Profile-field
// mapping", that scope carries the 7 custom claims.
// ──────────────────────────────────────────────────────────────────────

const moodleScopeName = decodeDotenvQuotedValue(process.env.MOODLE_OIDC_SCOPE_NAME || "moodle");

test.describe("moodle keycloak scope wiring (variant 0)", () => {
  test.skip(!oidcEnabled, "OIDC shared service disabled");

  test("Keycloak realm discovery advertises the moodle OIDC scope", async ({ request }) => {
    expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set in env").toBeTruthy();
    const r = await request.get(`${oidcIssuerUrl}/.well-known/openid-configuration`);
    expect(r.ok(), `discovery doc must be reachable at ${oidcIssuerUrl}`).toBeTruthy();
    const cfg = await r.json();
    expect(Array.isArray(cfg.scopes_supported), "scopes_supported must be an array").toBe(true);
    expect(
      cfg.scopes_supported.includes(moodleScopeName),
      `realm scopes_supported must contain "${moodleScopeName}"`
    ).toBe(true);
  });

  // End-to-end check: the Moodle-specific user-profile attribute
  // `middleName` is exposed by the realm's UserProfileProvider AND
  // round-trips through the Account REST API. Per req-015
  // §"Profile-field mapping" all 19 attributes are edit=user, so the
  // write must succeed. fetch() runs inside a real browser page so
  // it inherits the test's TLS trust / CA wrapper config.
  test("biber can edit middleName via Keycloak Account REST API and value persists", async ({ page }) => {
    expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set in env").toBeTruthy();
    expect(oidcClientId, "OIDC_CLIENT_ID must be set in env").toBeTruthy();

    // Navigate to the realm origin first so subsequent fetch() calls
    // share the browser's TLS trust / CA wrapper config.
    await page.goto(`${oidcIssuerUrl}/.well-known/openid-configuration`);

    const result = await page.evaluate(async ({ issuer, clientId, username, password }) => {
      const tokenForm = new URLSearchParams({
        grant_type: "password",
        client_id: clientId,
        username,
        password,
        scope: "openid"
      });
      const tokenResp = await fetch(`${issuer}/protocol/openid-connect/token`, {
        method: "POST",
        headers: { "content-type": "application/x-www-form-urlencoded", accept: "application/json" },
        body: tokenForm.toString()
      });
      const tokenBody = await tokenResp.text();
      if (!tokenResp.ok) return { stage: "token", status: tokenResp.status, body: tokenBody };
      const accessToken = JSON.parse(tokenBody).access_token;

      const auth = { authorization: `Bearer ${accessToken}`, accept: "application/json" };

      const metaResp = await fetch(`${issuer}/account/?userProfileMetadata=true`, { headers: auth });
      const metaBody = await metaResp.text();
      if (!metaResp.ok) return { stage: "meta", status: metaResp.status, body: metaBody };
      const meta = JSON.parse(metaBody);

      const probe = `MN-${Date.now()}`;
      const original = (meta.attributes && meta.attributes.middleName)
        ? meta.attributes.middleName
        : null;
      const update = {
        ...meta,
        attributes: { ...(meta.attributes || {}), middleName: [probe] }
      };
      delete update.userProfileMetadata;

      const upResp = await fetch(`${issuer}/account/`, {
        method: "POST",
        headers: { ...auth, "content-type": "application/json" },
        body: JSON.stringify(update)
      });
      const upBody = await upResp.text();
      if (!upResp.ok) return { stage: "update", status: upResp.status, body: upBody };

      const verifyResp = await fetch(`${issuer}/account/`, { headers: auth });
      const verifyBody = await verifyResp.text();
      if (!verifyResp.ok) return { stage: "verify", status: verifyResp.status, body: verifyBody };
      const verified = JSON.parse(verifyBody);

      // Restore the original middleName so the realm stays clean
      // across test re-runs without manual cleanup.
      const restoreAttrs = { ...(verified.attributes || {}) };
      if (original) {
        restoreAttrs.middleName = original;
      } else {
        delete restoreAttrs.middleName;
      }
      const restore = { ...verified, attributes: restoreAttrs };
      delete restore.userProfileMetadata;
      await fetch(`${issuer}/account/`, {
        method: "POST",
        headers: { ...auth, "content-type": "application/json" },
        body: JSON.stringify(restore)
      });

      return {
        stage: "ok",
        attrNames: (meta.userProfileMetadata?.attributes || []).map(a => a.name),
        probe,
        verifiedMiddleName: verified.attributes?.middleName?.[0]
      };
    }, {
      issuer: oidcIssuerUrl,
      clientId: oidcClientId,
      username: biberUsername,
      password: biberPassword
    });

    expect(
      result.stage,
      `flow must reach ok stage; got stage=${result.stage} status=${result.status} body=${(result.body || "").slice(0, 200)}`
    ).toBe("ok");
    expect(
      result.attrNames,
      "Account user-profile metadata must include the Moodle 'middleName' attribute"
    ).toContain("middleName");
    expect(
      result.verifiedMiddleName,
      "middleName value must round-trip after Account REST update"
    ).toBe(result.probe);
  });
});

// ──────────────────────────────────────────────────────────────────────
// LAM-as-independent-verifier (variant 0 + LAM enabled)
// Proves that a Keycloak-side profile edit propagates ALL the way down
// into the LDAP server, observable through a separate LDAP browser
// (LAM) that does NOT touch Keycloak — closing the loop on the
// WRITABLE federation contract from req-015.
// ──────────────────────────────────────────────────────────────────────

test.describe("keycloak → ldap write-through, verified via LAM", () => {
  test.skip(!oidcEnabled, "OIDC shared service disabled");
  test.skip(!lamEnabled,  "LAM not deployed (SERVICE_LAM=false)");

  test("middleName edited in Keycloak appears in LDAP via LAM", async ({ page, context }) => {
    expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set in env").toBeTruthy();
    expect(oidcClientId,  "OIDC_CLIENT_ID must be set in env").toBeTruthy();
    expect(lamBaseUrl,    "LAM_BASE_URL must be set in env").toBeTruthy();
    expect(lamPassword,   "LAM_PASSWORD must be set in env").toBeTruthy();

    const probe = `LAM-${Date.now()}`;

    // 1) Push the probe into Keycloak via the Account REST API.
    //    Same fetch-from-page-context pattern as the round-trip test.
    await page.goto(`${oidcIssuerUrl}/.well-known/openid-configuration`);
    const restResult = await page.evaluate(async ({ issuer, clientId, username, password, probe }) => {
      const tokenResp = await fetch(`${issuer}/protocol/openid-connect/token`, {
        method: "POST",
        headers: { "content-type": "application/x-www-form-urlencoded", accept: "application/json" },
        body: new URLSearchParams({
          grant_type: "password", client_id: clientId,
          username, password, scope: "openid"
        }).toString()
      });
      const tokenBody = await tokenResp.text();
      if (!tokenResp.ok) return { stage: "token", status: tokenResp.status, body: tokenBody };
      const accessToken = JSON.parse(tokenBody).access_token;
      const auth = { authorization: `Bearer ${accessToken}`, accept: "application/json" };

      const meta = await (await fetch(`${issuer}/account/?userProfileMetadata=true`, { headers: auth })).json();
      const update = { ...meta, attributes: { ...(meta.attributes || {}), middleName: [probe] } };
      delete update.userProfileMetadata;
      const upResp = await fetch(`${issuer}/account/`, {
        method: "POST",
        headers: { ...auth, "content-type": "application/json" },
        body: JSON.stringify(update)
      });
      if (!upResp.ok) return { stage: "update", status: upResp.status, body: await upResp.text() };
      return { stage: "ok" };
    }, { issuer: oidcIssuerUrl, clientId: oidcClientId, username: biberUsername, password: biberPassword, probe });

    expect(
      restResult.stage,
      `Keycloak write must succeed: stage=${restResult.stage} status=${restResult.status}`
    ).toBe("ok");

    // 2) Open LAM in a fresh tab so the Keycloak session above does not
    //    bleed in. LAM's lam-public default profile uses LDAP-bind
    //    auth — admin password is the LDAP root-bind password.
    const lamPage = await context.newPage();
    await lamPage.goto(`${lamBaseUrl}/templates/login.php`, { waitUntil: "load" });

    const lamPwInput = lamPage.locator("input[name='password'], input#passwd").first();
    await expect(lamPwInput, "LAM login form must render").toBeVisible({ timeout: 30_000 });
    await lamPwInput.fill(lamPassword);
    await lamPage.locator("button[type='submit'], input[type='submit']").first().click();
    await lamPage.waitForLoadState("networkidle");

    // 3) Navigate to biber's user entry. LAM's tree view exposes each
    //    user under the configured user OU — we drive a search by uid
    //    so the test is independent of the tree-rendering nuances.
    await lamPage.goto(`${lamBaseUrl}/templates/lists/list.php?type=user`, { waitUntil: "load" });
    const filter = lamPage.locator("input[name='filter_uid'], input[name*='filter']").first();
    if (await filter.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await filter.fill(biberUsername);
      await filter.press("Enter");
      await lamPage.waitForLoadState("networkidle");
    }
    const biberLink = lamPage.locator(`a:has-text("${biberUsername}")`).first();
    await expect(biberLink, "biber must appear in LAM user list").toBeVisible({ timeout: 30_000 });
    await biberLink.click();
    await lamPage.waitForLoadState("networkidle");

    // 4) Read the rendered user attributes; assert the probe appears.
    //    LAM displays attributes as `<label>: <value>` rows; we match
    //    the value anywhere in the page body to stay version-tolerant.
    await expect(
      lamPage.locator("body"),
      `LAM-rendered LDAP entry for ${biberUsername} must contain probe "${probe}" — ` +
      "proves Keycloak Account REST → WRITABLE federation → LDAP write-through"
    ).toContainText(probe, { timeout: 30_000 });
  });
});
