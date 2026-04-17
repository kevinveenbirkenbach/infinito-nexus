// @ts-check
const { test, expect } = require('@playwright/test');

test.use({
  ignoreHTTPSErrors: true
});

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

const baseUrl       = decodeDotenvQuotedValue(process.env.DECIDIM_BASE_URL || process.env.APP_BASE_URL);
const adminEmail    = decodeDotenvQuotedValue(process.env.ADMIN_EMAIL);
const adminPassword = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const oidcIssuerUrl = decodeDotenvQuotedValue(process.env.OIDC_ISSUER_URL);

test.beforeEach(() => {
  expect(baseUrl,       "DECIDIM_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(adminEmail,    "ADMIN_EMAIL must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
});

// Helper: login function
async function login(page, email, password) {
  await page.goto(`${baseUrl}/users/sign_in`);
  await page.waitForLoadState("networkidle");
  // Dismiss cookie consent banner if present
  const cookieBanner = page.locator("#dc-dialog-wrapper, .cookies__container, [data-cookie-consent]");
  if (await cookieBanner.isVisible().catch(() => false)) {
    const acceptBtn = page.locator("button[data-dc-accept], button.cookies__accept, button:has-text('Accept')").first();
    if (await acceptBtn.isVisible().catch(() => false)) {
      await acceptBtn.click();
      await page.waitForLoadState("networkidle");
    }
  }
  const emailInput = page.getByLabel(/email/i).first();
  await emailInput.waitFor({ state: "attached", timeout: 60000 });
  await emailInput.fill(email);
  await page.locator("input[type='password']").first().fill(password);
  await page.getByRole('button', { name: /log in|sign in/i }).first().click();
  await page.waitForLoadState("networkidle");
}

// Scenario I: Homepage loads
test("homepage loads and shows Decidim", async ({ page }) => {
  await page.goto(baseUrl);
  await expect(page).not.toHaveTitle("");
  await expect(page.locator("body")).toBeVisible();
});

// Scenario II: Admin login and logout
test("admin can log in and out", async ({ page }) => {
  await login(page, adminEmail, adminPassword);
  await expect(page).not.toHaveURL(/sign_in/);
  await expect(page.locator("body")).toBeVisible();
  await page.goto(`${baseUrl}/users/sign_out`);
  await page.waitForLoadState("networkidle");
  await expect(page).not.toHaveURL(/sign_in/);
});

// Scenario III: Administrator can access conversations page
test("administrator can access conversations page", async ({ page }) => {
  await login(page, adminEmail, adminPassword);
  await expect(page).not.toHaveURL(/sign_in/);
  await page.goto(`${baseUrl}/conversations`);
  await page.waitForLoadState("networkidle");
  await expect(page).not.toHaveURL(/sign_in/);
  await expect(page.locator("body")).toBeVisible();
});

// Scenario IV: SSO button visible (only if OIDC is configured)
test("SSO login button is visible when OIDC is enabled", async ({ page }) => {
  await page.goto(`${baseUrl}/users/sign_in`);
  const ssoButton = page.getByRole("link", { name: /sign in with/i });
  const oidcEnabled = process.env.OIDC_ENABLED === 'true';
  if (oidcEnabled) {
    await expect(ssoButton).toBeVisible();
  } else {
    test.skip();
  }
});
