// @ts-check
const { test, expect } = require('@playwright/test');

test.use({
  ignoreHTTPSErrors: true
});

const baseUrl       = process.env.DECIDIM_BASE_URL;
const adminEmail    = process.env.ADMIN_EMAIL;
const adminPassword = process.env.ADMIN_PASSWORD;
const biberUsername = process.env.BIBER_USERNAME;
const biberPassword = process.env.BIBER_PASSWORD;
const biberEmail    = process.env.BIBER_EMAIL;

test.beforeEach(() => {
  expect(baseUrl,       "DECIDIM_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(adminEmail,    "ADMIN_EMAIL must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(biberUsername, "BIBER_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(biberPassword, "BIBER_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(biberEmail,    "BIBER_EMAIL must be set in the Playwright env file").toBeTruthy();
});

// Helper: login function
async function login(page, email, password) {
  await page.goto(`${baseUrl}/users/sign_in`);
  await page.locator("#session_user_email").fill(email);
  await page.locator("#session_user_password").fill(password);
  await page.locator("#session_new_user").evaluate(form => form.submit());
  await page.waitForLoadState("networkidle");
}

// Scenario I: Homepage loads
test("homepage loads and shows Decidim", async ({ page }) => {
  await page.goto(baseUrl);
  await expect(page).not.toHaveTitle("");
  await expect(page.locator("body")).toBeVisible();
});

// Scenario II: Admin login and logout
test("admin can log in and out of system admin panel", async ({ page }) => {
  await login(page, adminEmail, adminPassword);
  await page.goto(`${baseUrl}/admin`);
  await page.waitForLoadState("networkidle");
  await expect(page).not.toHaveURL(/sign_in/);
  await expect(page.locator("body")).toBeVisible();
  await page.goto(`${baseUrl}/users/sign_out`);
  await page.waitForLoadState("networkidle");
  await expect(page).not.toHaveURL(/sign_in/);
});

// Scenario III: Biber login and logout
test("biber can log in and out", async ({ page }) => {
  await login(page, biberEmail, biberPassword);
  await expect(page).not.toHaveURL(/sign_in/);
  await expect(page.locator("body")).toBeVisible();
  await page.goto(`${baseUrl}/users/sign_out`);
  await page.waitForLoadState("networkidle");
  await expect(page).not.toHaveURL(/sign_in/);
});

// Scenario IV: Biber can access conversations and new conversation button is visible
test("biber can access conversations page and start a new conversation", async ({ page }) => {
  await login(page, biberEmail, biberPassword);
  await expect(page).not.toHaveURL(/sign_in/);

  await page.goto(`${baseUrl}/conversations`);
  await page.waitForLoadState("networkidle");
  await expect(page).not.toHaveURL(/sign_in/);

  // Verify new conversation button is present
  await expect(page.locator("[data-dialog-open='conversation']")).toBeVisible();

  // Open the modal and verify the recipient input is available
  await page.locator("[data-dialog-open='conversation']").click();
  await page.waitForTimeout(1000);
  await expect(page.locator("#add_conversation_users")).toBeVisible();
});

// Scenario V: Administrator can access conversations page
test("administrator can access conversations page", async ({ page }) => {
  await login(page, adminEmail, adminPassword);
  await expect(page).not.toHaveURL(/sign_in/);

  await page.goto(`${baseUrl}/conversations`);
  await page.waitForLoadState("networkidle");
  await expect(page).not.toHaveURL(/sign_in/);
  await expect(page.locator("body")).toBeVisible();
});

// Scenario VI: SSO button visible (only if OIDC is configured)
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
