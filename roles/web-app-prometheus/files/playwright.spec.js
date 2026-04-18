const { test, expect } = require("@playwright/test");

test.use({
  ignoreHTTPSErrors: true
});

function decodeDotenvQuotedValue(value) {
  if (typeof value !== "string" || value.length < 2) {
    return value;
  }

  if (!(value.startsWith('"') && value.endsWith('"'))) {
    return value;
  }

  const encoded = value.slice(1, -1);

  try {
    return JSON.parse(`"${encoded}"`).replace(/\$\$/g, "$");
  } catch {
    return encoded.replace(/\$\$/g, "$");
  }
}

// `docker --env-file` preserves the quotes emitted by `dotenv_quote`,
// so normalize these values before building URLs or typing credentials.
const oidcIssuerUrl      = decodeDotenvQuotedValue(process.env.OIDC_ISSUER_URL);
const prometheusBaseUrl  = decodeDotenvQuotedValue(process.env.PROMETHEUS_BASE_URL);
const adminUsername      = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword      = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const biberUsername      = decodeDotenvQuotedValue(process.env.BIBER_USERNAME);
const biberPassword      = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD);

// Perform SSO login via Keycloak.
// Accepts either a Page or a FrameLocator (when Keycloak is inside the dashboard iframe).
async function performOidcLogin(locator, username, password) {
  const usernameField = locator.getByRole("textbox", { name: /username|email/i });
  const passwordField = locator.getByRole("textbox", { name: "Password" });
  const signInButton  = locator.getByRole("button", { name: /sign in/i });

  await usernameField.waitFor({ state: "visible", timeout: 60_000 });
  await usernameField.fill(username);
  await usernameField.press("Tab");
  await passwordField.fill(password);
  await signInButton.click();
}

// Log out via the universal logout endpoint.
async function prometheusLogout(page, baseUrl) {
  await page.goto(`${baseUrl.replace(/\/$/, "")}/logout`, { waitUntil: "commit" }).catch(() => {});
}

test.beforeEach(() => {
  expect(oidcIssuerUrl,     "OIDC_ISSUER_URL must be set in the Playwright env file").toBeTruthy();
  expect(prometheusBaseUrl, "PROMETHEUS_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(adminUsername,     "ADMIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword,     "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(biberUsername,     "BIBER_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(biberPassword,     "BIBER_PASSWORD must be set in the Playwright env file").toBeTruthy();
});

// Scenario I: /metricz exposes prometheus-format metrics — no auth required.
//
// /metricz is the central nginx metrics endpoint scraped by prometheus once for all apps.
// It must be accessible without authentication (prometheus scrapes it without bearer tokens).
// If this returns 401/403 the nginx ACL whitelist for /metricz is misconfigured.
// If it returns HTML the location = /metricz block is missing from the nginx vhost config.
test("metricz endpoint is accessible and returns prometheus text format", async ({ request }) => {
  const metriczUrl = `${prometheusBaseUrl.replace(/\/$/, "")}/metricz`;
  const response = await request.get(metriczUrl);

  expect(
    response.status(),
    `/metricz must return 200 without auth — got ${response.status()}. ` +
    "If 401/403 the nginx ACL whitelist is misconfigured. If 200 with HTML, the location block is missing."
  ).toBe(200);

  const body = await response.text();

  expect(
    body,
    "/metricz response must be prometheus text format (lines starting with #) — got HTML or empty"
  ).toMatch(/^#/m);

  expect(
    body,
    "/metricz must expose nginx_http_requests_total — lua-resty-prometheus metric not found"
  ).toContain("nginx_http_requests_total");
});

// Scenario II: dashboard → click Prometheus → SSO login inside iframe (as admin) → verify Prometheus UI → logout
//
// Prometheus is admin-only (allowed_groups: web-app-prometheus-administrator).
// Clicking the Prometheus link on the dashboard opens it inside a fullscreen iframe.
// oauth2-proxy redirects unauthenticated requests to Keycloak, which loads inside that iframe.
// The outer page URL reflects the iframe URL via the `?iframe=` query parameter.
test("dashboard to prometheus: admin sso login, verify ui, logout", async ({ page }) => {
  const expectedOidcAuthUrl       = `${oidcIssuerUrl.replace(/\/$/, "")}/protocol/openid-connect/auth`;
  const expectedPrometheusBaseUrl = prometheusBaseUrl.replace(/\/$/, "");

  // 1. Navigate to dashboard and click the Prometheus app link
  await page.goto("/");
  await page.getByRole("link", { name: /Explore Prometheus/i }).click();

  // 2. Dashboard embeds Prometheus in a fullscreen iframe. oauth2-proxy redirects to Keycloak.
  //    Outer page URL: dashboard.infinito.example/?iframe=<encoded-keycloak-auth-url>&fullwidth=1...
  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `Expected dashboard URL to embed Keycloak OIDC auth: ${expectedOidcAuthUrl}`
    })
    .toContain(encodeURIComponent(expectedOidcAuthUrl));

  // 3. Fill admin credentials inside the dashboard iframe (Keycloak is rendered inside it)
  const appFrame = page.frameLocator("iframe").first();
  await performOidcLogin(appFrame, adminUsername, adminPassword);

  // 4. After successful auth, the iframe navigates to Prometheus.
  //    Outer page URL updates: dashboard.infinito.example/?iframe=<encoded-prometheus-url>...
  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `Expected dashboard URL to embed Prometheus: ${expectedPrometheusBaseUrl}`
    })
    .toContain(encodeURIComponent(expectedPrometheusBaseUrl));

  // 5. Verify Prometheus UI is loaded inside the iframe.
  //    The Prometheus v3.x nav always exposes "Graph", "Alerts", and "Status" links.
  await expect(
    appFrame.getByRole("link", { name: /^(Graph|Alerts|Status)$/i }).first()
  ).toBeVisible({ timeout: 30_000 });

  // 6. Logout via universal logout endpoint (navigates away from dashboard)
  await prometheusLogout(page, expectedPrometheusBaseUrl);

  // 7. Verify session is gone — oauth2-proxy redirects unauthenticated requests to Keycloak
  await page.goto(`${expectedPrometheusBaseUrl}/`, { waitUntil: "domcontentloaded" });
  await expect
    .poll(() => page.url(), {
      timeout: 15_000,
      message: "Expected redirect to Keycloak after logout"
    })
    .toContain(expectedOidcAuthUrl);

  await page.goto("/");
});

// Scenario II: biber (non-admin) navigates directly to Prometheus → SSO login → access denied
//
// biber is a regular authenticated user but is NOT in the web-app-prometheus-administrator group.
// After successfully authenticating with Keycloak, oauth2-proxy checks the groups claim and
// returns HTTP 403 — biber must never reach the Prometheus UI.
test("prometheus: biber is denied access after sso login", async ({ browser }) => {
  const expectedOidcAuthUrl       = `${oidcIssuerUrl.replace(/\/$/, "")}/protocol/openid-connect/auth`;
  const expectedPrometheusBaseUrl = prometheusBaseUrl.replace(/\/$/, "");

  // Use an isolated browser context so this test has no shared session with other tests.
  const biberContext = await browser.newContext({ ignoreHTTPSErrors: true });

  try {
    const biberPage = await biberContext.newPage();

    // Register the callback listener BEFORE goto to guarantee no response is missed.
    // In fast local environments the entire redirect chain (goto → Keycloak → callback)
    // can complete before a listener registered after performOidcLogin would start,
    // causing waitForResponse to catch a 200 sub-resource instead of the real response.
    //
    // oauth2-proxy hits /oauth2/callback after the Keycloak login:
    //   • user NOT in allowed_groups → 403 (biber's expected path)
    //   • user IS in allowed_groups  → 302 redirect to the app (admin's path)
    const callbackResponsePromise = biberPage.waitForResponse(
      (res) => res.url().includes("/oauth2/callback"),
      { timeout: 60_000 }
    );

    // 1. Navigate directly to Prometheus — oauth2-proxy redirects to Keycloak
    await biberPage.goto(`${expectedPrometheusBaseUrl}/`);

    await expect
      .poll(() => biberPage.url(), {
        timeout: 30_000,
        message: `Expected redirect to Keycloak OIDC auth: ${expectedOidcAuthUrl}`
      })
      .toContain(expectedOidcAuthUrl);

    // 2. Log in as biber via Keycloak
    await performOidcLogin(biberPage, biberUsername, biberPassword);

    // 3. Await the callback response — must be 403 (biber is not in prometheus-administrator group)
    const callbackResponse = await callbackResponsePromise;

    expect(
      callbackResponse.status(),
      `Expected oauth2-proxy to deny biber with 403 at /oauth2/callback, got ${callbackResponse.status()}`
    ).toBe(403);

  } finally {
    await biberContext.close().catch(() => {});
  }
});
