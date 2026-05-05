// End-to-end smoke tests for the OpenCloud role.
//
// Two scenarios:
//   1. administrator persona — SSO login lands on Files view, body shows
//      the LDAP `uid`-derived username.
//   2. biber persona — same flow exercised in an isolated browser context
//      to cover a non-admin LDAP user (matches the nextcloud convention).
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

const issuerPattern = new RegExp(issuerUrl.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
const baseUrlPattern = new RegExp(`^${baseUrl.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`);

async function ssoLoginAndAssertUsername(page, username, password) {
  await page.goto(baseUrl);
  await page.waitForURL(issuerPattern, { timeout: 30_000 });

  await page.locator('input[name="username"], #username').fill(username);
  await page.locator('input[name="password"], #password').fill(password);
  await page.getByRole("button", { name: /sign in|log in/i }).click();

  await page.waitForURL(baseUrlPattern, { timeout: 30_000 });
  await expect(page.locator("body")).toContainText(username, { timeout: 30_000 });
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
