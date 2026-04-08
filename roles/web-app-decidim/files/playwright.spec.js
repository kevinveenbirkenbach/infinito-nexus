// @ts-check
const { test, expect } = require('@playwright/test');
const { execSync } = require('child_process');

const baseUrl         = process.env.DECIDIM_BASE_URL;
const adminEmail      = process.env.ADMIN_EMAIL;
const adminPassword   = process.env.ADMIN_PASSWORD;
const oidcIssuerUrl   = process.env.OIDC_ISSUER_URL;

test.beforeEach(() => {
  expect(baseUrl,       "DECIDIM_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(adminEmail,    "ADMIN_EMAIL must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
});

// Scenario I: Load homepage
test("homepage loads and shows Decidim", async ({ page }) => {
  // 1. Navigate to homepage
  await page.goto(baseUrl);

  // 2. Expect page to load successfully
  await expect(page).toHaveTitle(/Decidim/i);
});

// Scenario II: Admin login
test("admin can log in to system admin panel", async ({ page }) => {
  // 1. Navigate to admin sign in
  await page.goto(`${baseUrl}/admin`);

  // 2. Fill in credentials
  await page.getByLabel("Email").fill(adminEmail);
  await page.getByLabel("Password").fill(adminPassword);

  // 3. Submit login form
  await page.getByRole("button", { name: /sign in/i }).click();

  // 4. Verify admin dashboard loaded
  await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
});

// Scenario III: Admin logout
test("admin can log out", async ({ page }) => {
  // 1. Log in first
  await page.goto(`${baseUrl}/admin`);
  await page.getByLabel("Email").fill(adminEmail);
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();

  // 2. Log out
  await page.getByRole("link", { name: /sign out/i }).click();

  // 3. Verify redirected to homepage
  await expect(page).toHaveURL(baseUrl + "/");
});

// Scenario IV: OIDC SSO button visible on login page
test("SSO login button is visible when OIDC is enabled", async ({ page }) => {
  // 1. Navigate to sign in page
  await page.goto(`${baseUrl}/users/sign_in`);

  // 2. Verify SSO button is present
  await expect(page.getByRole("link", { name: /sign in with/i })).toBeVisible();
});
