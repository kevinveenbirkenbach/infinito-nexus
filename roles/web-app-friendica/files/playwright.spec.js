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

const friendicaBaseUrl = decodeDotenvQuotedValue(process.env.FRIENDICA_BASE_URL);
const adminUsername    = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword    = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const biberUsername    = decodeDotenvQuotedValue(process.env.BIBER_USERNAME);
const biberPassword    = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD);

// Friendica authenticates users directly against its local DB. The openldap
// bridge is provided by the `ldapauth` addon: users typed into the Friendica
// login form are resolved against the shared openldap server, which already
// contains `administrator` and `biber`. No OIDC redirect step is involved.
async function performFriendicaLogin(page, baseUrl, username, password) {
  await page.goto(`${baseUrl}/login`, { waitUntil: "domcontentloaded" });

  const usernameField = page.locator("input[name='username']");
  const passwordField = page.locator("input[name='password']");

  // Friendica renders a `btn form-button-search` submit in the topbar before
  // the main login form, so a generic `button[type='submit']` selector picks
  // up the search button. Target the login form's own "Sign in" button by
  // accessible role + exact name instead.
  const signInButton = page.getByRole("button", { name: "Sign in", exact: true });

  await usernameField.waitFor({ state: "visible", timeout: 60_000 });
  await usernameField.fill(username);
  await passwordField.fill(password);

  await Promise.all([
    page.waitForLoadState("domcontentloaded"),
    signInButton.click(),
  ]);
}

// Wait until the post-login Friendica UI is rendered. The sidebar nav always
// exposes the `#navbar-apps-menu` / profile button for authenticated users.
async function waitForFriendicaHome(page) {
  const profileMenu = page.locator("#topbar-first, #navbar-apps-menu, a[href*='/logout']").first();
  await profileMenu.waitFor({ state: "visible", timeout: 60_000 });
}

// Log out via the universal logout endpoint. Every app's nginx vhost intercepts
// `location = /logout` and proxies it to web-svc-logout, which invalidates all
// active sessions. `waitUntil: 'commit'` avoids ERR_ABORTED from the multi-
// domain redirect chain the service triggers after session invalidation.
async function friendicaLogout(page, baseUrl) {
  await page.goto(`${baseUrl.replace(/\/$/, "")}/logout`, { waitUntil: "commit" }).catch(() => {});
}

test.beforeEach(() => {
  expect(friendicaBaseUrl, "FRIENDICA_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(adminUsername,    "ADMIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword,    "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(biberUsername,    "BIBER_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(biberPassword,    "BIBER_PASSWORD must be set in the Playwright env file").toBeTruthy();
});

// Scenario I: dashboard → click Friendica → verify iframe → login as admin → logout.
test("dashboard to friendica: admin login, verify ui, logout", async ({ page }) => {
  const expectedFriendicaBaseUrl = friendicaBaseUrl.replace(/\/$/, "");

  // 1. Open dashboard and click the Friendica card.
  await page.goto("/");
  await page.getByRole("link", { name: /Explore Friendica/i }).click();

  // 2. The dashboard embeds Friendica in a fullscreen iframe.
  await expect(page.locator("#main iframe")).toBeVisible({ timeout: 30_000 });

  // 3. Log in as administrator (navigates the top-level page, not the iframe).
  await performFriendicaLogin(page, expectedFriendicaBaseUrl, adminUsername, adminPassword);
  await waitForFriendicaHome(page);

  // 4. Log out via the universal logout endpoint.
  await friendicaLogout(page, expectedFriendicaBaseUrl);

  // 5. Confirm the session is gone — an unauthenticated request to /network
  //    must not render the authenticated nav.
  await page.goto(`${expectedFriendicaBaseUrl}/network`, { waitUntil: "domcontentloaded" }).catch(() => {});
  await expect(page.locator("a[href*='/logout']")).not.toBeAttached({ timeout: 10_000 });

  await page.goto("/");
});

// Scenario II: biber sends a DM to administrator, administrator reads it.
//
// Isolated browser contexts model two separate users on separate machines —
// no shared cookies or sessions between biber and admin.
test("friendica: biber sends direct message to administrator, administrator receives it", async ({ browser }) => {
  const expectedFriendicaBaseUrl = friendicaBaseUrl.replace(/\/$/, "");
  const testSubject              = `Playwright test ${Date.now()}`;
  const testBody                 = `Friendica DM body ${testSubject}`;

  const biberContext = await browser.newContext({ ignoreHTTPSErrors: true });
  const adminContext = await browser.newContext({ ignoreHTTPSErrors: true });

  try {
    // --- Part 1: biber logs in and sends a DM to administrator ---
    const biberPage = await biberContext.newPage();

    await performFriendicaLogin(biberPage, expectedFriendicaBaseUrl, biberUsername, biberPassword);
    await waitForFriendicaHome(biberPage);

    // Friendica's "new message" composer lives at /message/new/<recipient>.
    // Using the direct URL avoids depending on UI labels that change across
    // Friendica versions and localisations.
    await biberPage.goto(`${expectedFriendicaBaseUrl}/message/new/${adminUsername}`, {
      waitUntil: "domcontentloaded",
    });

    const subjectField = biberPage.locator("input[name='subject']");
    const bodyField    = biberPage.locator("textarea[name='body']");

    await subjectField.waitFor({ state: "visible", timeout: 30_000 });
    await subjectField.fill(testSubject);
    await bodyField.fill(testBody);

    // Same first-submit-button hazard as the login form: the topbar's search
    // button would win a generic selector. Scope to the composer's own submit.
    const sendButton = biberPage.getByRole("button", { name: /^(submit|send)$/i }).last();
    await Promise.all([
      biberPage.waitForLoadState("domcontentloaded"),
      sendButton.click(),
    ]);

    await friendicaLogout(biberPage, expectedFriendicaBaseUrl);

    // --- Part 2: administrator reads the DM ---
    const adminPage = await adminContext.newPage();

    await performFriendicaLogin(adminPage, expectedFriendicaBaseUrl, adminUsername, adminPassword);
    await waitForFriendicaHome(adminPage);

    await adminPage.goto(`${expectedFriendicaBaseUrl}/message`, { waitUntil: "domcontentloaded" });

    // The subject is unique per run, so it pins the assertion to the DM just
    // sent rather than any pre-existing mailbox entry.
    await expect(adminPage.getByText(testSubject).first()).toBeVisible({ timeout: 30_000 });

    await friendicaLogout(adminPage, expectedFriendicaBaseUrl);
  } finally {
    await biberContext.close().catch(() => {});
    await adminContext.close().catch(() => {});
  }
});
