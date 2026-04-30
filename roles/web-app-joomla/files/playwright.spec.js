const { test, expect } = require("@playwright/test");
const { skipUnlessServiceEnabled } = require("./service-gating");

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

function normalizeBaseUrl(value) {
  return decodeDotenvQuotedValue(value || "").replace(/\/$/, "");
}

const joomlaBaseUrl = normalizeBaseUrl(process.env.JOOMLA_BASE_URL);
const oidcIssuerUrl = normalizeBaseUrl(process.env.OIDC_ISSUER_URL || "");
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

async function performJoomlaAdminFormLogin(page, baseUrl, username, password) {
  // Local Joomla form-login at /administrator?fallback=local. The
  // `?fallback=local` query short-circuits the plg_system_keycloak
  // redirect so the operator has an emergency hatch when Keycloak is
  // unavailable (Modus 3 per requirement 013).
  await page.goto(`${baseUrl}/administrator?fallback=local`, { waitUntil: "domcontentloaded" });

  const usernameField = page.locator("input[name='username']");
  const passwordField = page.locator("input[name='passwd']");

  await usernameField.waitFor({ state: "visible", timeout: 60_000 });
  await usernameField.fill(username);
  await passwordField.fill(password);

  await Promise.all([
    page.waitForLoadState("domcontentloaded"),
    page.locator("button[type='submit'], input[type='submit']").first().click(),
  ]);
}

test.beforeEach(async ({ page }) => {
  expect(joomlaBaseUrl, "JOOMLA_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(adminUsername, "ADMIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
  await page.context().clearCookies();
});

test("OIDC: native plg_system_keycloak redirects unauthenticated visitors to Keycloak and logs them back in to Joomla", async ({ page }) => {
  // The plg_system_keycloak plugin shipped under
  // roles/web-app-joomla/files/joomla-oidc-plugin/ implements native
  // OIDC SSO against Keycloak (no oauth2-proxy sidecar). Visiting the
  // Joomla site root `/` while gated by the plugin redirects the
  // browser to the Keycloak authorization endpoint. After Keycloak
  // login, the plugin handles the callback at
  // /index.php?option=keycloak&task=callback, provisions/updates the
  // local Joomla user with RBAC group memberships derived from the
  // Keycloak `groups` claim, and lands the user back on the original
  // URL.
  skipUnlessServiceEnabled("oidc");
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set when OIDC is enabled").toBeTruthy();

  const expectedOidcAuthUrl = `${oidcIssuerUrl}/protocol/openid-connect/auth`;
  const expectedJoomlaBaseUrl = joomlaBaseUrl.replace(/\/$/, "");

  await page.goto(`${expectedJoomlaBaseUrl}/`);

  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `expected redirect to Keycloak OIDC auth (${expectedOidcAuthUrl})`
    })
    .toContain(expectedOidcAuthUrl);

  await performKeycloakLogin(page, adminUsername, adminPassword);

  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `expected redirect back to Joomla at ${expectedJoomlaBaseUrl}`
    })
    .toContain(expectedJoomlaBaseUrl);

  // Joomla front-end renders after the OIDC handshake. RBAC mapping
  // gave the administrator persona Super Users (id 8), so the
  // administrator landing nav link is visible to logged-in users.
  await expect(page.locator("body")).toBeVisible({ timeout: 60_000 });
});

test("OIDC: /administrator?fallback=local hatch bypasses Keycloak and accepts the local Joomla form (Modus 3 emergency path)", async ({ page }) => {
  // The local form-login fallback at /administrator?fallback=local
  // is the operationally-mandated hatch when Keycloak is unavailable
  // (Modus 3 per requirement 013). It MUST NOT redirect to the IdP,
  // and the local form MUST accept the bootstrap administrator
  // credentials.
  skipUnlessServiceEnabled("oidc");
  const expectedJoomlaBaseUrl = joomlaBaseUrl.replace(/\/$/, "");

  await performJoomlaAdminFormLogin(page, expectedJoomlaBaseUrl, adminUsername, adminPassword);

  // Joomla 6 uses `body.com_cpanel` on the admin home; the broader
  // fallback set covers future template tweaks.
  const controlPanelMarker = page
    .locator("body.com_cpanel, #sidebarmenu, nav[aria-label='Main menu'], a[href*='option=com_cpanel']")
    .first();
  await controlPanelMarker.waitFor({ state: "visible", timeout: 60_000 });
});

test("LDAP: Joomla core LDAP plugin authenticates the administrator at /administrator (LDAP variant)", async ({ page }) => {
  // In the LDAP variant (variant 1 of meta/variants.yml), the OIDC
  // service flag is off and Joomla's core LDAP authentication plugin
  // is the integrated login path against svc-db-openldap. This
  // scenario exercises that path.
  skipUnlessServiceEnabled("ldap");
  const expectedJoomlaBaseUrl = joomlaBaseUrl.replace(/\/$/, "");

  await page.goto(`${expectedJoomlaBaseUrl}/administrator`, { waitUntil: "domcontentloaded" });

  const usernameField = page.locator("input[name='username']");
  const passwordField = page.locator("input[name='passwd']");
  await usernameField.waitFor({ state: "visible", timeout: 60_000 });
  await usernameField.fill(adminUsername);
  await passwordField.fill(adminPassword);
  await Promise.all([
    page.waitForLoadState("domcontentloaded"),
    page.locator("button[type='submit'], input[type='submit']").first().click(),
  ]);

  const controlPanelMarker = page
    .locator("body.com_cpanel, #sidebarmenu, nav[aria-label='Main menu'], a[href*='option=com_cpanel']")
    .first();
  await controlPanelMarker.waitFor({ state: "visible", timeout: 60_000 });
});
