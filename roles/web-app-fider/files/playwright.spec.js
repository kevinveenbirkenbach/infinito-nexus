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
const fiderBaseUrl   = decodeDotenvQuotedValue(process.env.FIDER_BASE_URL);
const adminUsername  = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword  = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const biberUsername  = decodeDotenvQuotedValue(process.env.BIBER_USERNAME);
const biberPassword  = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD);

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

// Click through Fider's sign-in page to reach the SSO provider button.
// Fider shows a "Sign in" button in the header, then a modal listing OAuth providers.
async function clickFiderSsoButton(locator) {
  // Click "Sign in" in the Fider header
  const signInLink = locator.getByRole("link", { name: /sign in/i });

  await signInLink.first().waitFor({ state: "visible", timeout: 30_000 });
  await signInLink.first().click();

  // Fider shows a "Join the conversation" modal with a "Continue with ... SSO" button.
  // The display_name is set to "{{ SOFTWARE_NAME }} SSO" = "Infinito.Nexus SSO".
  const ssoButton = locator.getByRole("link", { name: /continue with/i });

  await ssoButton.first().waitFor({ state: "visible", timeout: 15_000 });
  // force: true bypasses aria-disabled which Fider sets on the button during modal render
  await ssoButton.first().click({ force: true });
}

test.beforeEach(() => {
  expect(oidcIssuerUrl,  "OIDC_ISSUER_URL must be set in the Playwright env file").toBeTruthy();
  expect(fiderBaseUrl,   "FIDER_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(adminUsername,  "ADMIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword,  "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(biberUsername,  "BIBER_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(biberPassword,  "BIBER_PASSWORD must be set in the Playwright env file").toBeTruthy();
});

// Scenario I: dashboard → Fider → SSO login as admin → verify admin UI → logout
//
// Fider is a public feedback platform with native OIDC (no oauth2-proxy).
// The dashboard opens Fider in a fullscreen iframe. The Fider page loads publicly,
// then the user clicks Sign in → selects the Keycloak SSO provider → Keycloak login page
// loads inside the iframe → after login the iframe navigates back to Fider.
//
// NOTE: The outer dashboard URL (page.url()) does NOT update when the iframe navigates
// internally (e.g. to Keycloak and back). All navigation checks must target the iframe
// content directly rather than polling page.url() for an encoded inner URL.
test("dashboard to fider: admin sso login, verify ui, logout", async ({ page }) => {
  const expectedFiderBaseUrl = fiderBaseUrl.replace(/\/$/, "");

  // 1. Navigate to dashboard and open Fider
  await page.goto("/");
  await page.getByRole("link", { name: /Explore Fider/i }).click();

  // 2. The dashboard embeds Fider in a fullscreen iframe — confirm the iframe appeared
  await expect(page.locator("#main iframe")).toBeVisible({ timeout: 30_000 });

  const appFrame = page.frameLocator("#main iframe").first();

  // 3. Wait for the outer dashboard URL to reflect the embedded Fider URL
  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `Expected dashboard URL to embed Fider: ${expectedFiderBaseUrl}`
    })
    .toContain(encodeURIComponent(expectedFiderBaseUrl));

  // 4. Click through Fider's sign-in flow to trigger the Keycloak SSO redirect
  await clickFiderSsoButton(appFrame);

  // 5. Fider redirects the iframe to Keycloak for SSO login.
  //    The outer dashboard URL never changes when the iframe navigates, so we wait
  //    for the Keycloak login form to become visible inside the iframe directly.
  //    (performOidcLogin waits for the username field before filling credentials.)
  await performOidcLogin(appFrame, adminUsername, adminPassword);

  // 6. After login Fider redirects back inside the iframe — verify the admin
  //    is logged in (.c-menu-user is only rendered when fider.session.isAuthenticated)
  await expect(appFrame.locator(".c-menu-user").first()).toBeVisible({ timeout: 60_000 });

  // 7. Logout — navigate to Fider's sign-out endpoint
  await page.goto(`${expectedFiderBaseUrl}/signout`, { waitUntil: "domcontentloaded" }).catch(() => {});

  // 8. Verify signout — the public Fider page should no longer show the user menu
  await page.goto(`${expectedFiderBaseUrl}/`);
  await expect(page.locator(".c-menu-user")).not.toBeAttached({ timeout: 10_000 });

  await page.goto("/");
});

// Scenario II: biber logs in directly to Fider as a regular user → verifies access → logs out
//
// Fider is a public platform — any authenticated Keycloak user can log in.
// biber should be able to access Fider but will have a regular user role (not admin).
// This test verifies that the SSO flow works for non-admin users and that they land
// on the Fider main page (not an admin panel).
test("fider: biber sso login as regular user, verify access, logout", async ({ browser }) => {
  const expectedOidcAuthUrl  = `${oidcIssuerUrl.replace(/\/$/, "")}/protocol/openid-connect/auth`;
  const expectedFiderBaseUrl = fiderBaseUrl.replace(/\/$/, "");

  // Isolated context — no shared session with other tests
  const biberContext = await browser.newContext({ ignoreHTTPSErrors: true });

  try {
    const biberPage = await biberContext.newPage();

    // 1. Navigate directly to Fider
    await biberPage.goto(`${expectedFiderBaseUrl}/`);

    // 2. Fider public page loads — click Sign in → SSO provider
    await clickFiderSsoButton(biberPage);

    // 3. Wait for Keycloak OIDC auth
    await expect
      .poll(() => biberPage.url(), {
        timeout: 30_000,
        message: `Expected redirect to Keycloak OIDC auth: ${expectedOidcAuthUrl}`
      })
      .toContain(expectedOidcAuthUrl);

    // 4. Log in as biber
    await performOidcLogin(biberPage, biberUsername, biberPassword);

    // 5. After login Fider redirects back
    await expect
      .poll(() => biberPage.url(), {
        timeout: 60_000,
        message: `Expected redirect back to Fider after biber login: ${expectedFiderBaseUrl}`
      })
      .toContain(expectedFiderBaseUrl);

    // 6. Verify biber is logged in — .c-menu-user is only rendered when authenticated
    await expect(biberPage.locator(".c-menu-user").first()).toBeVisible({ timeout: 30_000 });

    // 7. Verify biber is NOT shown admin controls.
    //    The admin link is inside the dropdown AND gated by isCollaborator — so it is
    //    never in the DOM for a regular user (regardless of dropdown state).
    await expect(biberPage.locator("a[href='/admin']").first()).not.toBeAttached({ timeout: 5_000 });

    // 8. Logout
    await biberPage.goto(`${expectedFiderBaseUrl}/signout`, { waitUntil: "domcontentloaded" }).catch(() => {});

  } finally {
    await biberContext.close().catch(() => {});
  }
});
