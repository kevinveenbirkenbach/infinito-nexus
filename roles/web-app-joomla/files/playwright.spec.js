const { test, expect } = require("@playwright/test");

test.use({
  ignoreHTTPSErrors: true
});

function decodeDotenvQuotedValue(value) {
  if (typeof value !== "string" || value.length < 2) {
    return value;
  }

  if (!(value.startsWith('"') && value.endsWith('"'))) {
    return value;
  }

  const encoded = value.slice(1, -1);

  try {
    return JSON.parse(`"${encoded}"`).replace(/\$\$/g, "$");
  } catch {
    return encoded.replace(/\$\$/g, "$");
  }
}

const joomlaBaseUrl = decodeDotenvQuotedValue(process.env.JOOMLA_BASE_URL);
const adminUsername = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);

// Joomla has no OIDC integration in this stack — the administrator account is
// created locally from users.administrator.* during install. The login form
// lives at /administrator and posts directly to Joomla's auth handler.
async function performJoomlaAdminLogin(page, baseUrl, username, password) {
  await page.goto(`${baseUrl}/administrator`, { waitUntil: "domcontentloaded" });

  const usernameField = page.locator("input[name='username']");
  const passwordField = page.locator("input[name='passwd']");

  await usernameField.waitFor({ state: "visible", timeout: 60_000 });
  await usernameField.fill(username);
  await passwordField.fill(password);

  await Promise.all([
    page.waitForLoadState("domcontentloaded"),
    page.locator("button[type='submit'], input[type='submit']").first().click(),
  ]);
}

// Log out via the universal logout endpoint. Every app's nginx vhost intercepts
// `location = /logout` and proxies it to web-svc-logout. Using `waitUntil: 'commit'`
// avoids ERR_ABORTED from the multi-domain redirect chain.
async function joomlaLogout(page, baseUrl) {
  await page.goto(`${baseUrl.replace(/\/$/, "")}/logout`, { waitUntil: "commit" }).catch(() => {});
}

test.beforeEach(() => {
  expect(joomlaBaseUrl, "JOOMLA_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(adminUsername, "ADMIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
});

// Scenario: dashboard → click Joomla → verify iframe → admin login at /administrator
//           → verify control panel → logout.
//
// Joomla is a CMS, not a messaging platform — there is no cross-user DM flow
// to verify. The test covers the three things that matter for this stack:
// dashboard integration, admin login against the locally-provisioned account,
// and universal logout.
test("dashboard to joomla: admin login, verify control panel, logout", async ({ page }) => {
  const expectedJoomlaBaseUrl = joomlaBaseUrl.replace(/\/$/, "");

  // 1. Open dashboard and click the Joomla card.
  await page.goto("/");
  await page.getByRole("link", { name: /Explore Joomla/i }).click();

  // 2. The dashboard embeds Joomla in a fullscreen iframe.
  await expect(page.locator("#main iframe")).toBeVisible({ timeout: 30_000 });

  // 3. Log in to the Joomla admin control panel with the local administrator.
  await performJoomlaAdminLogin(page, expectedJoomlaBaseUrl, adminUsername, adminPassword);

  // 4. Verify the control panel rendered. Joomla 5 uses `body.com_cpanel` on
  //    the admin home; falling back to any administrator nav element covers
  //    future template tweaks without loosening the post-login assertion.
  const controlPanelMarker = page
    .locator("body.com_cpanel, #sidebarmenu, nav[aria-label='Main menu'], a[href*='option=com_cpanel']")
    .first();
  await controlPanelMarker.waitFor({ state: "visible", timeout: 60_000 });

  // 5. Log out via the universal logout endpoint.
  await joomlaLogout(page, expectedJoomlaBaseUrl);

  // 6. Confirm the admin session is gone — /administrator must render the
  //    login form again (empty username field) rather than the control panel.
  await page.goto(`${expectedJoomlaBaseUrl}/administrator`, { waitUntil: "domcontentloaded" }).catch(() => {});
  await expect(page.locator("input[name='username']")).toBeVisible({ timeout: 15_000 });

  await page.goto("/");
});
