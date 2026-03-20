const { test, expect } = require("@playwright/test");

test.use({
  ignoreHTTPSErrors: true
});

const loginUsername = process.env.LOGIN_USERNAME;
const loginPassword = process.env.LOGIN_PASSWORD;

test.beforeEach(() => {
  expect(loginUsername, "LOGIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(loginPassword, "LOGIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
});

test("dashboard to nextcloud login", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Explore Nextcloud" }).click();

  const nextcloudFrame = page.locator("#main iframe").contentFrame();

  await nextcloudFrame.getByRole("textbox", { name: "Username or email" }).click();
  await nextcloudFrame.getByRole("textbox", { name: "Username or email" }).fill(loginUsername);
  await nextcloudFrame.getByRole("textbox", { name: "Username or email" }).press("Tab");
  await nextcloudFrame.getByRole("textbox", { name: "Password" }).fill(loginPassword);
  await nextcloudFrame.getByText("Remember me").click();
  await nextcloudFrame.getByRole("button", { name: "Sign In" }).click();

  // First login may show the welcome modal; later logins usually skip it.
  const welcomeHeadline = nextcloudFrame.getByText("Welcome to Nextcloud!");
  const welcomeVisible = await welcomeHeadline
    .first()
    .waitFor({ state: "visible", timeout: 15000 })
    .then(() => true)
    .catch(() => false);

  if (welcomeVisible) {
    await nextcloudFrame
      .locator("div")
      .filter({ hasText: "Welcome to Nextcloud!" })
      .first()
      .click({ timeout: 5000 })
      .catch(() => {});
    await nextcloudFrame.getByRole("button", { name: /Close/i }).click({ timeout: 10000 });
  }

  await expect(nextcloudFrame.getByRole("button", { name: "Settings menu" })).toBeVisible({ timeout: 60000 });
  await nextcloudFrame.getByRole("button", { name: "Settings menu" }).click();
  await nextcloudFrame.getByRole("link", { name: "Log out" }).click();
  await nextcloudFrame.getByRole("button", { name: "Logout" }).click();
  await page.goto("/");
});
