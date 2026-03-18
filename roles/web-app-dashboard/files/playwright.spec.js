const { test } = require("@playwright/test");

test.use({
  ignoreHTTPSErrors: true
});

test("dashboard intentional failure", async ({ page }) => {
  await page.goto("/");
  throw new Error("Intentional dashboard Playwright failure for verification");
});
