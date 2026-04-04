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
});

// Scenario: dashboard → click Prometheus → SSO login inside iframe → verify Prometheus UI → logout
//
// Clicking the Prometheus link on the dashboard opens it inside a fullscreen iframe.
// oauth2-proxy redirects unauthenticated requests to Keycloak, which loads inside that iframe.
// The outer page URL reflects the iframe URL via the `?iframe=` query parameter.
test("dashboard to prometheus: sso login, verify ui, logout", async ({ page }) => {
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

  // 3. Fill credentials inside the dashboard iframe (Keycloak is rendered inside it)
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
