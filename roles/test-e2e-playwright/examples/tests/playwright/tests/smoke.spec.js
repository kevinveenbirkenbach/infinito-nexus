const { test, expect } = require("@playwright/test");

test("homepage is reachable", async ({ page }) => {
  const response = await page.goto("/", { waitUntil: "domcontentloaded" });

  expect(response).not.toBeNull();
  expect([200, 302].includes(response.status())).toBeTruthy();
  await expect(page).toHaveURL(/https?:\/\//);
});
