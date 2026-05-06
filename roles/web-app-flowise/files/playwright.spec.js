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

const baseUrl = normalizeBaseUrl(process.env.FLOWISE_BASE_URL || "");
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
  expect(baseUrl, "FLOWISE_BASE_URL must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  await page.context().clearCookies();
});

test("baseline: Flowise responds on the canonical domain", async ({ page }) => {
  const response = await page.goto(`${baseUrl}/`);
  expect(response, "Expected Flowise response").toBeTruthy();
  expect(response.status(), "Expected Flowise status < 500").toBeLessThan(500);
  expect(
    response.url().includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" to back the Flowise URL`
  ).toBe(true);
});

test("OIDC: oauth2-proxy redirects unauthenticated visitors through Keycloak (variant 0)", async ({ page }) => {
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
  await expect
    .poll(() => page.url(), {
      timeout: 90_000,
      message: `expected redirect back to Flowise at ${expectedBaseUrl}`
    })
    .toContain(expectedBaseUrl);
  await expect(page.locator("body")).toBeVisible({ timeout: 60_000 });
});

test("LDAP: same oauth2-proxy gate when Keycloak federates user storage from LDAP (variant 1)", async ({ page }) => {
  skipUnlessServiceEnabled("ldap");
  expect(adminUsername, "ADMIN_USERNAME must be set when LDAP is enabled").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set when LDAP is enabled").toBeTruthy();
  const expectedBaseUrl = baseUrl.replace(/\/$/, "");
  await page.goto(`${expectedBaseUrl}/`);
  await performKeycloakLogin(page, adminUsername, adminPassword);
  await expect
    .poll(() => page.url(), {
      timeout: 90_000,
      message: `expected redirect back to Flowise at ${expectedBaseUrl}`
    })
    .toContain(expectedBaseUrl);
  await expect(page.locator("body")).toBeVisible({ timeout: 60_000 });
});
