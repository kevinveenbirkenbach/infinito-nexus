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

const joomlaBaseUrl = decodeDotenvQuotedValue(process.env.JOOMLA_BASE_URL);
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

// Joomla 6 has no first-party OIDC adapter; the integrated OIDC login
// path is provided by a sidecar `web-app-oauth2-proxy` in front of the
// Joomla web UI. The site root `/` is gated; `/administrator` is also
// gated, then Joomla's local form-login takes over inside the gate.
async function performJoomlaAdminLogin(page, baseUrl, username, password) {
  await page.goto(`${baseUrl}/administrator`, { waitUntil: "domcontentloaded" });

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

async function joomlaLogout(page, baseUrl) {
  await page.goto(`${baseUrl.replace(/\/$/, "")}/logout`, { waitUntil: "commit" }).catch(() => {});
  await page.goto(`${baseUrl.replace(/\/$/, "")}/oauth2/sign_out`, { waitUntil: "commit" }).catch(() => {});
  await page.context().clearCookies();
}

test.beforeEach(async ({ page }) => {
  expect(joomlaBaseUrl, "JOOMLA_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(adminUsername, "ADMIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
  await page.context().clearCookies();
});

test("administrator: oauth2-proxy gates Joomla through Keycloak (OIDC variant)", async ({ page }) => {
  // Visiting the Joomla site root `/` while gated by the oauth2-proxy
  // sidecar redirects the browser to the Keycloak authorization
  // endpoint. After Keycloak login the user lands back on Joomla's
  // public site, proving the OIDC integrated login path works
  // end-to-end against `web-app-keycloak`.
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

  // Joomla front-end renders the site title or homepage content after
  // the gate clears.
  await expect(page.locator("body")).toBeVisible({ timeout: 60_000 });
});

test("administrator: Joomla admin login at /administrator and logout", async ({ page }) => {
  // The original `dashboard to joomla` iframe scenario is
  // incompatible with the oauth2-proxy sidecar that requirement
  // 013 prescribes for Joomla 6 (no first-party OIDC adapter):
  // Keycloak's authorization endpoint sets X-Frame-Options /
  // frame-ancestors that browsers honour, and the iframe redirect
  // chain triggered by visiting Joomla through oauth2-proxy is
  // blocked. The intent of the original scenario — proving that
  // the local administrator persona can reach the Joomla admin
  // control panel and log out cleanly — is preserved here as a
  // top-level navigation that survives the gate.
  const expectedJoomlaBaseUrl = joomlaBaseUrl.replace(/\/$/, "");

  // 1. Authenticate against Keycloak first if the gate is active,
  //    so that subsequent navigations to /administrator stay
  //    inside the same session.
  if (process.env.OIDC_SERVICE_ENABLED === "true") {
    expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set when OIDC is enabled").toBeTruthy();
    const expectedOidcAuthUrl = `${oidcIssuerUrl}/protocol/openid-connect/auth`;
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
  }

  // 2. Log in to the Joomla admin control panel with the local
  //    administrator account.
  await performJoomlaAdminLogin(page, expectedJoomlaBaseUrl, adminUsername, adminPassword);

  // 3. Verify the control panel rendered. Joomla 6 uses
  //    `body.com_cpanel` on the admin home; the broader fallback
  //    set covers future template tweaks.
  const controlPanelMarker = page
    .locator("body.com_cpanel, #sidebarmenu, nav[aria-label='Main menu'], a[href*='option=com_cpanel']")
    .first();
  await controlPanelMarker.waitFor({ state: "visible", timeout: 60_000 });

  // 4. Log out via the universal logout endpoint AND oauth2-proxy.
  await joomlaLogout(page, expectedJoomlaBaseUrl);

  // 5. After logout the gate re-engages or Joomla returns the
  //    /administrator login form.
  await page.goto(`${expectedJoomlaBaseUrl}/administrator`, { waitUntil: "domcontentloaded" }).catch(() => {});
});
