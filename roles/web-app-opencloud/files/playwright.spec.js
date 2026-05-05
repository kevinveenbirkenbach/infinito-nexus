// End-to-end smoke tests for the OpenCloud role.
//
// OpenCloud Web shows a local Login page (heading + emblem + "Login" button)
// when OIDC is configured. The SPA does not auto-redirect to the IdP, so the
// flow is: navigate to base URL -> wait for the Login button -> click it ->
// Keycloak credential form -> back to OpenCloud Files view.
const { test, expect } = require("@playwright/test");

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

const baseUrl = decodeDotenvQuotedValue(process.env.APP_BASE_URL);
const issuerUrl = decodeDotenvQuotedValue(process.env.OIDC_ISSUER_URL);
const adminUsername = decodeDotenvQuotedValue(process.env.LOGIN_USERNAME);
const adminPassword = decodeDotenvQuotedValue(process.env.LOGIN_PASSWORD);
const biberUsername = decodeDotenvQuotedValue(process.env.BIBER_USERNAME);
const biberPassword = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD);
const oidcEnabled = (process.env.OPENCLOUD_OIDC_ENABLED || "true").toLowerCase() === "true";

const issuerHost = new URL(issuerUrl).host;
const issuerPattern = new RegExp(`^https?://${issuerHost.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`);
const baseUrlPattern = new RegExp(`^${baseUrl.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`);

function attachDiagnostics(page, label) {
  const diagnostics = { console: [], requests: [], errors: [] };
  page.on("console", (msg) => {
    diagnostics.console.push(`[${msg.type()}] ${msg.text()}`);
  });
  page.on("pageerror", (err) => {
    diagnostics.errors.push(String(err));
  });
  page.on("requestfailed", (req) => {
    diagnostics.requests.push(`${req.failure()?.errorText || ""} ${req.method()} ${req.url()}`);
  });
  return diagnostics;
}

async function ssoLoginAndAssertUsername(page, username, password) {
  const diagnostics = attachDiagnostics(page, username);
  // OpenCloud Web's index.html shows a "browser not supported" splash unless
  // `forceAllowOldBrowser` is present in localStorage. Playwright's headless
  // Chromium UA is not on its allow list, so prime the flag for the host
  // before any navigation happens.
  await page.addInitScript(() => {
    try {
      window.localStorage.setItem(
        "forceAllowOldBrowser",
        JSON.stringify({ expiry: Date.now() + 30 * 24 * 60 * 60 * 1000 })
      );
    } catch (e) {}
  });
  await page.goto(baseUrl);

  const onIssuer = async () => issuerPattern.test(page.url());
  if (!(await onIssuer())) {
    // Either click the Login control on the OpenCloud SPA or wait for the
    // SPA to redirect to Keycloak. Try both in parallel and finish on
    // whichever happens first.
    const loginCta = page.locator(
      'button:has-text("Login"), button:has-text("Sign in"), button:has-text("Log in"), [data-test-id="login-button"], a[href*="oidc"]'
    );
    try {
      await Promise.race([
        page.waitForURL(issuerPattern, { timeout: 60_000 }),
        (async () => {
          await loginCta.first().waitFor({ state: "visible", timeout: 60_000 });
          await Promise.all([
            page.waitForURL(issuerPattern, { timeout: 60_000 }),
            loginCta.first().click(),
          ]);
        })(),
      ]);
    } catch (err) {
      const summary = [
        `URL when stuck: ${page.url()}`,
        `Console (${diagnostics.console.length}):`,
        ...diagnostics.console.slice(-25),
        `Page errors (${diagnostics.errors.length}):`,
        ...diagnostics.errors.slice(-10),
        `Failed requests (${diagnostics.requests.length}):`,
        ...diagnostics.requests.slice(-10),
      ].join("\n");
      throw new Error(`OpenCloud SPA never reached Keycloak.\n${summary}\nOriginal error: ${err}`);
    }
  }

  await page.locator('input[name="username"], #username').fill(username);
  await page.locator('input[name="password"], #password').fill(password);
  // Submitting via Enter on the password field avoids Playwright's
  // post-click stability wait that fails when the Sign-In button gets
  // detached during the multi-redirect chain back to OpenCloud.
  await page.locator('input[name="password"], #password').press("Enter");

  // Bypass OpenCloud's "browser not supported" splash if it appears.
  // Playwright's Chromium UA is not on the OpenCloud allow list, so the SPA
  // shows a splash with a "I want to continue anyway" button.
  const continueAnyway = page.getByRole("button", { name: /continue anyway/i });
  if (await continueAnyway.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await continueAnyway.click();
  }

  // The Files view is the post-login landing route; assert against the SPA
  // navigation banner instead of body text because OpenCloud shows the
  // username inside the user-menu drawer rather than in the page body.
  await expect(page.getByRole("banner", { name: /top bar/i })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("link", { name: /personal files/i })).toBeVisible({ timeout: 30_000 });
}

test("opencloud sso login (administrator) lands on files view", async ({ page }) => {
  test.skip(!oidcEnabled, "OIDC not enabled for this deployment");
  expect(adminUsername, "LOGIN_USERNAME must be set").toBeTruthy();
  expect(adminPassword, "LOGIN_PASSWORD must be set").toBeTruthy();

  await ssoLoginAndAssertUsername(page, adminUsername, adminPassword);
});

test("opencloud sso login (biber) lands on files view", async ({ browser }) => {
  test.skip(!oidcEnabled, "OIDC not enabled for this deployment");
  expect(biberUsername, "BIBER_USERNAME must be set").toBeTruthy();
  expect(biberPassword, "BIBER_PASSWORD must be set").toBeTruthy();

  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  try {
    await ssoLoginAndAssertUsername(page, biberUsername, biberPassword);
  } finally {
    await context.close();
  }
});
