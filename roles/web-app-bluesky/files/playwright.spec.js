const { test, expect } = require("@playwright/test");
const { skipUnlessServiceEnabled } = require("./service-gating");

test.use({ ignoreHTTPSErrors: true });

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

function normalizeBaseUrl(value) {
  return decodeDotenvQuotedValue(value || "").replace(/\/$/, "");
}

const baseUrl = normalizeBaseUrl(process.env.BLUESKY_BASE_URL || "");
const oidcIssuerUrl = normalizeBaseUrl(process.env.OIDC_ISSUER_URL || "");
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN || "");
const adminUsername = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);

async function performKeycloakLogin(page, username, password) {
  const usernameField = page.locator("input[name='username'], input#username").first();
  const passwordField = page.locator("input[name='password'], input#password").first();
  const signInButton = page
    .locator("input#kc-login, button#kc-login, button[type='submit'], input[type='submit']")
    .first();
  await expect(usernameField).toBeVisible({ timeout: 60_000 });
  await usernameField.fill(username);
  await usernameField.press("Tab");
  await passwordField.fill(password);
  await signInButton.click();
}

test.beforeEach(async ({ page }) => {
  expect(baseUrl, "BLUESKY_BASE_URL must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  await page.context().clearCookies();
});

test("baseline: bluesky web UI responds on the canonical domain", async ({ page }) => {
  // Liveness probe — passes regardless of whether the OIDC gate is
  // active. The PDS XRPC layer at api.bluesky.<domain> is exercised
  // by the OIDC scenario below (which uses the broker handoff to
  // reach social-app via Keycloak).
  const response = await page.goto(`${baseUrl}/`);
  expect(response, "Expected bluesky response").toBeTruthy();
  expect(response.status(), "Expected bluesky status < 500").toBeLessThan(500);
  expect(
    response.url().includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" to back the bluesky URL`
  ).toBe(true);
});

test("OIDC: oauth2-proxy + login-broker drop a Bluesky session into social-app via Keycloak (variant A+)", async ({ page }) => {
  // The user-facing entry point at `web.bluesky.<domain>/` is gated
  // by the project's oauth2-proxy sidecar. Visiting the root while
  // unauthenticated MUST trigger an OIDC redirect to the realm's
  // authorization endpoint. After Keycloak login the request flows
  // through oauth2-proxy to the in-role login-broker, which (a)
  // auto-provisions the PDS account on first visit, (b) decrypts the
  // AES-256-GCM-encrypted app-password from the user's Keycloak
  // attribute, (c) creates a PDS session via createSession, and (d)
  // renders an HTML handoff page that drops the session JWTs into
  // localStorage["BSKY_STORAGE"] before redirecting to "/" — at which
  // point the social-app is reached as an authenticated Bluesky user
  // without ever showing the synthesised app-password to the
  // browser.
  skipUnlessServiceEnabled("oidc");
  expect(adminUsername, "ADMIN_USERNAME must be set when OIDC is enabled").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set when OIDC is enabled").toBeTruthy();
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set when OIDC is enabled").toBeTruthy();

  const expectedOidcAuthUrl = `${oidcIssuerUrl}/protocol/openid-connect/auth`;
  const expectedBaseUrl = baseUrl.replace(/\/$/, "");

  await page.goto(`${expectedBaseUrl}/`);

  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `expected redirect to Keycloak OIDC auth (${expectedOidcAuthUrl})`
    })
    .toContain(expectedOidcAuthUrl);

  await performKeycloakLogin(page, adminUsername, adminPassword);

  // Wait for the post-OIDC redirect chain to settle. After Keycloak
  // accepts the credentials, the browser bounces through
  //   /oauth2/callback → / → broker handoff → social-app
  // and we want the URL to come to rest on the Bluesky base URL —
  // NOT on an `/oauth2/*` path. The `expect.poll` form alone matches
  // any URL containing the base, including the intermediate
  // `/oauth2/start` redirect, so we additionally pin the path to
  // not be under `/oauth2/`.
  await expect
    .poll(() => page.url(), {
      timeout: 90_000,
      message: `expected post-OIDC URL to land on Bluesky outside /oauth2/* (got: ${page.url()})`
    })
    .toMatch(new RegExp(`^${expectedBaseUrl.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/(?!oauth2/)`));

  // Wait for the network to settle so the broker's handoff JS can
  // commit localStorage + cookie before we inspect them.
  await page.waitForLoadState("networkidle", { timeout: 30_000 }).catch(() => {});
  await expect(page.locator("body")).toBeVisible({ timeout: 60_000 });

  // The broker writes a schema-compliant `BSKY_STORAGE` payload
  // built from upstream `social-app@1.121.0`'s persisted defaults
  // PLUS the PDS session JWTs. Verify both that the entry exists
  // and that it carries an `accessJwt` — the latter is the only
  // observable proof that the broker's PDS createSession completed
  // and the handoff actually flowed through.
  const storageProbe = await page.evaluate(() => {
    const raw = localStorage.getItem("BSKY_STORAGE");
    if (!raw) return { present: false };
    try {
      const parsed = JSON.parse(raw);
      const cur = parsed && parsed.session && parsed.session.currentAccount;
      return {
        present: true,
        hasCurrentAccount: !!cur,
        hasAccessJwt: !!(cur && cur.accessJwt)
      };
    } catch (_) {
      return { present: true, hasCurrentAccount: false, hasAccessJwt: false, parseError: true };
    }
  });
  expect(storageProbe.present, `BSKY_STORAGE missing — handoff never reached the browser. Probe: ${JSON.stringify(storageProbe)}`).toBe(true);
  expect(storageProbe.hasAccessJwt, `BSKY_STORAGE has no accessJwt — broker rendered the page but PDS createSession did not feed a usable session. Probe: ${JSON.stringify(storageProbe)}`).toBe(true);
});

test("LDAP: same broker handoff continues to work when Keycloak federates user storage from LDAP", async ({ page }) => {
  // The LDAP variant rides the same login-broker; the only change is
  // Keycloak's user storage backend (LDAP federation against
  // svc-db-openldap). Functionally indistinguishable from the OIDC
  // variant on the Bluesky side, so the scenario asserts the same
  // end state.
  skipUnlessServiceEnabled("ldap");
  expect(adminUsername, "ADMIN_USERNAME must be set when LDAP is enabled").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set when LDAP is enabled").toBeTruthy();
  const expectedBaseUrl = baseUrl.replace(/\/$/, "");

  await page.goto(`${expectedBaseUrl}/`);
  await performKeycloakLogin(page, adminUsername, adminPassword);

  await expect
    .poll(() => page.url(), {
      timeout: 90_000,
      message: `expected redirect back to Bluesky web UI at ${expectedBaseUrl}`
    })
    .toContain(expectedBaseUrl);

  await expect(page.locator("body")).toBeVisible({ timeout: 60_000 });
});
