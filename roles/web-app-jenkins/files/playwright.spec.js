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

const baseUrl = normalizeBaseUrl(process.env.JENKINS_BASE_URL || "");
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
  expect(baseUrl, "JENKINS_BASE_URL must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  await page.context().clearCookies();
});

test("baseline: Jenkins responds on the canonical domain", async ({ page }) => {
  const r = await page.goto(`${baseUrl}/login`);
  expect(r).toBeTruthy();
  expect(r.status()).toBeLessThan(500);
});

test("OIDC: oic-auth plugin redirects unauthenticated visitors through Keycloak (variant 0)", async ({ page }) => {
  skipUnlessServiceEnabled("oidc");
  expect(adminUsername).toBeTruthy(); expect(adminPassword).toBeTruthy(); expect(oidcIssuerUrl).toBeTruthy();
  const expectedAuth = `${oidcIssuerUrl}/protocol/openid-connect/auth`;
  const expectedBase = baseUrl.replace(/\/$/, "");
  await page.goto(`${expectedBase}/`);
  await expect.poll(() => page.url(), { timeout: 60_000 }).toContain(expectedAuth);
  await performKeycloakLogin(page, adminUsername, adminPassword);
  await expect.poll(() => page.url(), { timeout: 90_000 }).toContain(expectedBase);
  await expect(page.locator("body")).toBeVisible({ timeout: 60_000 });
});

test("LDAP: Jenkins LDAP plugin authenticates against svc-db-openldap (variant 1)", async ({ page }) => {
  skipUnlessServiceEnabled("ldap");
  const expectedBase = baseUrl.replace(/\/$/, "");
  // Jenkins LDAP login uses the local /login form rather than an
  // OIDC redirect; pin to the form path so the spec doesn't bounce
  // through Keycloak.
  await page.goto(`${expectedBase}/login`);
  const u = page.locator("input[name='j_username']").first();
  const p = page.locator("input[name='j_password']").first();
  await expect(u).toBeVisible({ timeout: 60_000 });
  await u.fill(adminUsername);
  await p.fill(adminPassword);
  await page.locator("button[name='Submit'], input[type='submit']").first().click();
  await expect(page.locator("body")).toBeVisible({ timeout: 60_000 });
});
