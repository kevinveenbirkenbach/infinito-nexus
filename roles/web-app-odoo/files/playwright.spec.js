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
const oidcIssuerUrl  = decodeDotenvQuotedValue(process.env.OIDC_ISSUER_URL);
const odooBaseUrl    = decodeDotenvQuotedValue(process.env.ODOO_BASE_URL);
const adminUsername  = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword  = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);

// Perform SSO login via Keycloak.
// Accepts a Page or FrameLocator (when Keycloak loads inside the dashboard iframe).
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

// Click the "Login with SSO" button on Odoo's login page.
// When auth_oauth is installed Odoo renders OAuth provider links in .o_auth_oauth_providers.
// The oe_login_form has class 'd-none' (hidden) when OAuth providers are present,
// so we must NOT wait for the form - we wait for the provider links directly.
async function clickOdooSsoButton(locator) {
  // Wait for the OAuth provider list to appear
  const providerList = locator.locator(".o_auth_oauth_providers");
  await providerList.first().waitFor({ state: "visible", timeout: 60_000 });

  // Click the SSO provider link by its text
  const ssoButton = locator.getByRole("link", { name: /login with sso/i });
  await ssoButton.first().waitFor({ state: "visible", timeout: 15_000 });
  await ssoButton.first().click();
}

// Check if user is authenticated in Odoo
// Odoo is a SPA - after login, the web client loads asynchronously.
// We check multiple indicators: the web client container, navbar elements,
// user menu, or the URL not being on the login page.
async function isOdooAuthenticated(locator) {
  try {
    // Primary indicators: web client root container that appears after successful load
    const webClient = locator.locator(".o_web_client");
    const actionManager = locator.locator(".o_action_manager");
    const mainNavbar = locator.locator(".o_main_navbar");
    
    // Secondary indicators: specific UI elements for logged-in users
    const userMenu = locator.locator(".o_user_menu");
    const appsIcon = locator.locator(".o_navbar_apps_menu, .o_menu_toggle");
    const homeMenu = locator.locator(".o_home_menu");
    
    // Any of these indicates successful authentication
    return (
      await webClient.first().isVisible().catch(() => false) ||
      await actionManager.first().isVisible().catch(() => false) ||
      await mainNavbar.first().isVisible().catch(() => false) ||
      await userMenu.first().isVisible().catch(() => false) ||
      await appsIcon.first().isVisible().catch(() => false) ||
      await homeMenu.first().isVisible().catch(() => false)
    );
  } catch {
    return false;
  }
}

// Perform logout from Odoo by navigating the iframe directly to the logout URL.
// This avoids "Target crashed" errors that occur when clicking menu items
// causes the iframe to navigate and detach.
async function performOdooLogout(page, odooBaseUrl) {
  const logoutUrl = odooBaseUrl.replace(/\/$/, "") + "/web/session/logout";
  
  // Navigate the main page to load the logout URL in the iframe
  // The dashboard's ?iframe= parameter will load the given URL
  await page.goto(`/?iframe=${encodeURIComponent(logoutUrl)}`);
  
  // Give the logout a moment to process
  await page.waitForTimeout(2_000);
}

// Check if we're on the login page (logged out state)
async function isOnOdooLoginPage(locator) {
  try {
    const loginForm = locator.locator(".oe_login_form, form[action='/web/login']");
    return await loginForm.first().isVisible().catch(() => false);
  } catch {
    return false;
  }
}

// Wait for frame URL to contain a specific string
async function waitForFrameUrl(iframeLocator, matcher, timeout, errorMessage) {
  await expect
    .poll(
      async () => {
        const iframeHandle = await iframeLocator.elementHandle();
        const frame = iframeHandle ? await iframeHandle.contentFrame() : null;
        return frame ? frame.url() : "";
      },
      {
        timeout,
        message: errorMessage
      }
    )
    .toContain(matcher);
}

// Helper to check visibility
async function isVisible(locator) {
  return locator.first().isVisible().catch(() => false);
}

// Log out from dashboard if needed
async function logoutFromDashboardIfNeeded(page) {
  const nav = page.locator("nav");
  const loginItem = nav.getByText("Login", { exact: true });
  const logoutItem = nav.getByText("Logout", { exact: true });

  await expect
    .poll(
      async () =>
        (await isVisible(loginItem)) ||
        (await isVisible(logoutItem)),
      {
        timeout: 60_000,
        message: "Expected dashboard to expose either Login or Logout entry"
      }
    )
    .toBe(true);

  if (await isVisible(loginItem) && !(await isVisible(logoutItem))) {
    return;
  }

  if (await isVisible(logoutItem)) {
    await logoutItem.first().click();
    await page.waitForTimeout(1_000);
  }

  await expect
    .poll(
      async () => (await isVisible(loginItem)) && !(await isVisible(logoutItem)),
      {
        timeout: 60_000,
        message: "Expected dashboard to show the Login entry again after logout"
      }
    )
    .toBe(true);
}

test.beforeEach(() => {
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set in the Playwright env file").toBeTruthy();
  expect(odooBaseUrl, "ODOO_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(adminUsername, "ADMIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
});

// Scenario I: dashboard → Odoo → SSO login as admin → verify authenticated → logout
//
// Odoo ERP with native OIDC via auth_oauth module (no oauth2-proxy).
// The dashboard opens Odoo in a fullscreen iframe. Odoo loads the login page,
// user clicks "Login with SSO" → Keycloak login page loads inside the iframe →
// after login the iframe navigates back to Odoo authenticated.
test("dashboard to odoo: admin sso login, verify ui, logout", async ({ page }) => {
  const expectedOdooBaseUrl = odooBaseUrl.replace(/\/$/, "");
  const odooLoginUrl = expectedOdooBaseUrl + "/web/login";

  // 1. Navigate to dashboard with the Odoo login URL pre-loaded in the iframe.
  // The dashboard's ?iframe= parameter auto-opens the given URL in #main iframe.
  await page.goto(`/?iframe=${encodeURIComponent(odooLoginUrl)}`);

  // 2. Wait for the iframe to appear and load the Odoo login URL
  await expect(page.locator("#main iframe")).toBeVisible({ timeout: 30_000 });

  const appFrame = page.frameLocator("#main iframe").first();

  // 3. Wait for the iframe URL to reflect the Odoo login URL
  await waitForFrameUrl(
    page.locator("#main iframe"),
    "/web/login",
    60_000,
    `Expected iframe to load Odoo login at ${odooLoginUrl}`
  );

  // 4. Click the "Login with SSO" button (waits internally for provider list)
  await clickOdooSsoButton(appFrame);

  // 5. After clicking SSO, the iframe navigates to Keycloak.
  // Re-acquire the frame locator after navigation since the iframe URL changes.
  await waitForFrameUrl(
    page.locator("#main iframe"),
    oidcIssuerUrl.replace(/\/$/, ""),
    60_000,
    "Expected iframe to navigate to Keycloak for authentication"
  );

  // 6. Perform OIDC login with admin credentials
  const keycloakFrame = page.frameLocator("#main iframe").first();
  await performOidcLogin(keycloakFrame, adminUsername, adminPassword);

  // 7. Wait for navigation back to Odoo after authentication.
  // The URL must contain the Odoo base URL but NOT /web/login (which would mean auth failed).
  await expect
    .poll(
      async () => {
        const iframeHandle = await page.locator("#main iframe").first().elementHandle();
        const frame = iframeHandle ? await iframeHandle.contentFrame() : null;
        const url = frame ? frame.url() : "";
        return url.includes(expectedOdooBaseUrl) && !url.includes("/web/login");
      },
      {
        timeout: 60_000,
        message: "Expected iframe to navigate back to Odoo authenticated area (not login page)"
      }
    )
    .toBe(true);

  // 8. Reacquire frame after redirect back to Odoo
  const odooFrameAuth = page.frameLocator("#main iframe").first();

  // 9. Verify the user is authenticated (Odoo shows apps/user menu)
  await expect
    .poll(
      async () => await isOdooAuthenticated(odooFrameAuth),
      {
        timeout: 60_000,
        message: "Expected Odoo to show authenticated user interface"
      }
    )
    .toBe(true);

  // 10. Perform logout from Odoo by navigating to the logout URL
  await performOdooLogout(page, odooBaseUrl);

  // 11. Verify we're back on the login page (provider list visible again)
  const odooFrameAfterLogout = page.frameLocator("#main iframe").first();
  await expect
    .poll(
      async () => await isVisible(odooFrameAfterLogout.locator(".o_auth_oauth_providers")),
      {
        timeout: 60_000,
        message: "Expected Odoo to return to login page after logout"
      }
    )
    .toBe(true);

  // 12. Return to dashboard and verify logged out state
  await page.goto("/");
  await logoutFromDashboardIfNeeded(page);
});
