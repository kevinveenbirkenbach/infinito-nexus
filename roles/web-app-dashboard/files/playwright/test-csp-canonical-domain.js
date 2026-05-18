const { test, expect } = require("@playwright/test");

exports.register = function (shared) {
  test("dashboard enforces Content-Security-Policy and exposes canonical domain from applications lookup", async ({ page }) => {
    const response = await page.goto("/");
    expect(response, "Expected dashboard landing response").toBeTruthy();
    expect(response.status(), "Expected dashboard landing response to be successful").toBeLessThan(400);

    const directives = shared.assertCspResponseHeader(response, "dashboard landing");
    await shared.assertCspMetaParity(page, directives, "dashboard landing");

    const documentHtml = await response.text();
    const documentUrl = response.url();
    expect(
      documentHtml.includes(shared.env.canonicalDomain) || documentUrl.includes(shared.env.canonicalDomain),
      `Expected canonical domain "${shared.env.canonicalDomain}" (from applications lookup) to appear in the dashboard document`
    ).toBe(true);

    await shared.waitForDashboardReady(page);
    await shared.expectNoCspViolations(page, null, "dashboard landing");
  });
};
