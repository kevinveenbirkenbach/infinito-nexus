const { test, expect } = require("@playwright/test");
const { skipUnlessServiceEnabled } = require("./service-gating");

test.use({ ignoreHTTPSErrors: true });

function decodeDotenvQuotedValue(value) {
  if (typeof value !== "string" || value.length < 2) return value;
  if (!(value.startsWith('"') && value.endsWith('"'))) return value;
  const encoded = value.slice(1, -1);
  try { return JSON.parse(`"${encoded}"`).replace(/\$\$/g, "$"); }
  catch { return encoded.replace(/\$\$/g, "$"); }
}
function normalizeBaseUrl(value) { return decodeDotenvQuotedValue(value || "").replace(/\/$/, ""); }

const baseUrl = normalizeBaseUrl(process.env.BASEROW_BASE_URL || "");
const oidcIssuerUrl = normalizeBaseUrl(process.env.OIDC_ISSUER_URL || "");
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN || "");
const adminUsername = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);

async function performKeycloakLogin(page, username, password) {
  const u = page.locator("input[name='username'], input#username").first();
  const p = page.locator("input[name='password'], input#password").first();
  const b = page.locator("input#kc-login, button#kc-login, button[type='submit'], input[type='submit']").first();
  await expect(u).toBeVisible({ timeout: 60_000 });
  await u.fill(username); await u.press("Tab"); await p.fill(password); await b.click();
}

test.beforeEach(async ({ page }) => {
  expect(baseUrl, "BASEROW_BASE_URL must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  await page.context().clearCookies();
});

test("baseline: Baserow responds on the canonical domain", async ({ page }) => {
  const r = await page.goto(`${baseUrl}/`);
  expect(r, "Expected Baserow response").toBeTruthy();
  expect(r.status(), "Expected Baserow status < 500").toBeLessThan(500);
  expect(r.url().includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" to back the Baserow URL`).toBe(true);
});

test("OIDC: oauth2-proxy redirects unauthenticated visitors through Keycloak (variant 0)", async ({ page }) => {
  skipUnlessServiceEnabled("oidc");
  expect(adminUsername).toBeTruthy(); expect(adminPassword).toBeTruthy(); expect(oidcIssuerUrl).toBeTruthy();
  const expectedAuth = `${oidcIssuerUrl}/protocol/openid-connect/auth`;
  const expectedBase = baseUrl.replace(/\/$/, "");
  await page.goto(`${expectedBase}/`);
  await expect.poll(() => page.url(), { timeout: 60_000, message: `expected redirect to ${expectedAuth}` }).toContain(expectedAuth);
  await performKeycloakLogin(page, adminUsername, adminPassword);
  await expect.poll(() => page.url(), { timeout: 90_000, message: `expected redirect back to ${expectedBase}` }).toContain(expectedBase);
  await expect(page.locator("body")).toBeVisible({ timeout: 60_000 });
});

test("LDAP: same oauth2-proxy gate when Keycloak federates user storage from LDAP (variant 1)", async ({ page }) => {
  skipUnlessServiceEnabled("ldap");
  expect(adminUsername).toBeTruthy(); expect(adminPassword).toBeTruthy();
  const expectedBase = baseUrl.replace(/\/$/, "");
  await page.goto(`${expectedBase}/`);
  await performKeycloakLogin(page, adminUsername, adminPassword);
  await expect.poll(() => page.url(), { timeout: 90_000, message: `expected redirect back to ${expectedBase}` }).toContain(expectedBase);
  await expect(page.locator("body")).toBeVisible({ timeout: 60_000 });
});
