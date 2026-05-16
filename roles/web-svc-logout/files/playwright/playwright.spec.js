const { test, expect } = require("@playwright/test");
const { decodeDotenvQuotedValue, runAdminFlow, runBiberFlow, runGuestFlow } = require("./personas");

test.use({ ignoreHTTPSErrors: true });

const appBaseUrl = decodeDotenvQuotedValue(process.env.APP_BASE_URL);
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN);

test.beforeEach(() => {
  expect(appBaseUrl, "APP_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set in the Playwright env file").toBeTruthy();
});

const logoutTargetRoles = (() => {
  const raw = process.env.LOGOUT_TARGET_ROLES_JSON || "[]";
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
})();

for (const target of logoutTargetRoles) {
  test(`universal-logout injected in ${target.id} (${target.canonical_domain})`, async ({ page }) => {
    expect(
      target.canonical_url,
      `Expected canonical_url in LOGOUT_TARGET_ROLES_JSON entry for ${target.id}`
    ).toBeTruthy();
    const targetUrl = `${target.canonical_url}/`;
    await page.goto(targetUrl, { waitUntil: "domcontentloaded" });
    const html = await page.content();

    expect(
      html,
      `Expected universal-logout 'logout.js' script reference in ${target.id} HTML body`
    ).toContain("logout.js");
  });
}

// Persona scenarios.
// Bodies live in the shared helper roles/test-e2e-playwright/files/personas.js
// so every role's persona flow stays consistent.

test("guest: public-landing → auth chain → never authenticated", async ({ page }) => {
  await runGuestFlow(page);
});

test("biber: app → universal logout", async ({ page }) => {
  await runBiberFlow(page);
});

test("administrator: app → universal logout", async ({ page }) => {
  await runAdminFlow(page);
});
