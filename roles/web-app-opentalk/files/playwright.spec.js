// End-to-end smoke tests for the OpenTalk role.
//
// Two scenarios mirroring the nextcloud convention:
//   1. administrator persona — SSO login lands on the OpenTalk dashboard,
//      body shows the LDAP `uid`-derived username.
//   2. biber persona — same flow in an isolated browser context.
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
const oidcEnabled = (process.env.OPENTALK_OIDC_ENABLED || "true").toLowerCase() === "true";

const issuerPattern = new RegExp(issuerUrl.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
const baseUrlPattern = new RegExp(`^${baseUrl.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`);
const signInLabel = /sign in|log in|anmelden/i;

async function ssoLoginAndAssertUsername(page, username, password) {
  await page.goto(baseUrl);

  // The frontend either auto-redirects to Keycloak or renders a "Sign in"
  // CTA first. Click the CTA when present, otherwise wait for the redirect.
  const signInCta = page.getByRole("button", { name: signInLabel });
  if (await signInCta.first().isVisible({ timeout: 5_000 }).catch(() => false)) {
    await signInCta.first().click();
  }
  await page.waitForURL(issuerPattern, { timeout: 30_000 });

  await page.locator('input[name="username"], #username').fill(username);
  await page.locator('input[name="password"], #password').fill(password);
  await page.getByRole("button", { name: /sign in|log in/i }).click();

  await page.waitForURL(baseUrlPattern, { timeout: 30_000 });
  await expect(page.locator("body")).toContainText(username, { timeout: 30_000 });
}

test("opentalk sso login (administrator) lands on dashboard", async ({ page }) => {
  test.skip(!oidcEnabled, "OIDC not enabled for this deployment");
  expect(adminUsername, "LOGIN_USERNAME must be set").toBeTruthy();
  expect(adminPassword, "LOGIN_PASSWORD must be set").toBeTruthy();

  await ssoLoginAndAssertUsername(page, adminUsername, adminPassword);
});

test("opentalk sso login (biber) lands on dashboard", async ({ browser }) => {
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
