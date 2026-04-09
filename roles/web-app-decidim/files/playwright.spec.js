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

// Scenario I: Homepage loads
test("homepage loads and shows Decidim", async ({ page }) => {
  await page.goto(baseUrl);
  await expect(page).toHaveTitle(/Decidim/i);
});

// Scenario II: Admin login and logout
test("admin can log in and out of system admin panel", async ({ page }) => {
  // 1. Navigate to admin sign in
  await page.goto(`${baseUrl}/admin`);

  // 2. Fill in credentials
  await page.getByLabel("Email").fill(adminEmail);
  await page.getByLabel("Password").fill(adminPassword);

  // 3. Submit
  await page.getByRole("button", { name: /sign in/i }).click();

  // 4. Verify admin dashboard loaded
  await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();

  // 5. Log out
  await page.getByRole("link", { name: /sign out/i }).click();
  await expect(page).toHaveURL(baseUrl + "/");
});

// Scenario III: Biber login and logout
test("biber can log in and out", async ({ page }) => {
  // 1. Navigate to sign in
  await page.goto(`${baseUrl}/users/sign_in`);

  // 2. Fill in biber credentials
  await page.getByLabel("Email").fill(biberEmail);
  await page.getByLabel("Password").fill(biberPassword);

  // 3. Submit
  await page.getByRole("button", { name: /sign in/i }).click();

  // 4. Verify logged in
  await expect(page.getByText(biberUsername)).toBeVisible();

  // 5. Log out
  await page.getByRole("link", { name: /sign out/i }).click();
  await expect(page).toHaveURL(baseUrl + "/");
});

// Scenario IV: Biber sends message to administrator
test("biber can send a message to administrator", async ({ page }) => {
  // 1. Log in as biber
  await page.goto(`${baseUrl}/users/sign_in`);
  await page.getByLabel("Email").fill(biberEmail);
  await page.getByLabel("Password").fill(biberPassword);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByText(biberUsername)).toBeVisible();

  // 2. Navigate to conversations
  await page.goto(`${baseUrl}/conversations/new`);

  // 3. Search for administrator
  await page.getByPlaceholder(/search/i).fill("administrator");
  await page.getByRole("option", { name: /administrator/i }).click();

  // 4. Type and send message
  await page.getByLabel(/message/i).fill("Hello Administrator, this is a test message from Biber.");
  await page.getByRole("button", { name: /send/i }).click();

  // 5. Verify message sent
  await expect(page.getByText("Hello Administrator")).toBeVisible();
});

// Scenario V: Administrator replies to biber
test("administrator can reply to biber message", async ({ page }) => {
  // 1. Log in as administrator
  await page.goto(`${baseUrl}/users/sign_in`);
  await page.getByLabel("Email").fill(adminEmail);
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: /sign in/i }).click();

  // 2. Navigate to conversations
  await page.goto(`${baseUrl}/conversations`);

  // 3. Open conversation from biber
  await page.getByRole("link", { name: new RegExp(biberUsername, 'i') }).first().click();

  // 4. Reply
  await page.getByLabel(/message/i).fill("Hello Biber, this is a reply from Administrator.");
  await page.getByRole("button", { name: /send/i }).click();

  // 5. Verify reply sent
  await expect(page.getByText("Hello Biber")).toBeVisible();
});

// Scenario VI: SSO button visible
test("SSO login button is visible when OIDC is enabled", async ({ page }) => {
  await page.goto(`${baseUrl}/users/sign_in`);
  await expect(page.getByRole("link", { name: /sign in with/i })).toBeVisible();
});
