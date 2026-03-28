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

// `docker --env-file` preserves the quotes emitted by `dotenv_quote`,
// so normalize these values before building URLs or typing credentials.
const oidcIssuerUrl  = decodeDotenvQuotedValue(process.env.OIDC_ISSUER_URL);
const mailuBaseUrl   = decodeDotenvQuotedValue(process.env.MAILU_BASE_URL);
const adminUsername  = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword  = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const adminEmail     = decodeDotenvQuotedValue(process.env.ADMIN_EMAIL);
const biberUsername  = decodeDotenvQuotedValue(process.env.BIBER_USERNAME);
const biberPassword  = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD);
const biberEmail     = decodeDotenvQuotedValue(process.env.BIBER_EMAIL);

async function waitForFirstVisible(page, locators, timeout = 60_000) {
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    for (const locator of locators) {
      if (await locator.first().isVisible().catch(() => false)) {
        return locator.first();
      }
    }

    await page.waitForTimeout(500);
  }

  throw new Error("Timed out waiting for one of the expected selectors to become visible");
}

// Mailu's heviat OIDC fork shows its own /sso/login page with a local login form AND an
// "SSO Login" link that redirects to Keycloak. Click that link specifically.
// Use openid-connect/auth (not just openid-connect) to avoid accidentally clicking the logout
// link (openid-connect/logout) which is also present in the Roundcube interface.
async function clickThroughMailuSsoPage(frame) {
  const oidcLink = frame.locator("a[href*='openid-connect/auth']").first();

  if (await oidcLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await oidcLink.click();
  }
}

// Perform SSO login via Keycloak inside a frame context (or page context for direct navigation).
// Works for both iframe-embedded and full-page Mailu flows.
async function performOidcLogin(frame, username, password) {
  const usernameField = frame.getByRole("textbox", { name: /username|email/i });
  const passwordField = frame.getByRole("textbox", { name: "Password" });
  const signInButton  = frame.getByRole("button", { name: /sign in/i });

  await usernameField.waitFor({ state: "visible", timeout: 60_000 });
  await usernameField.fill(username);
  await usernameField.press("Tab");
  await passwordField.fill(password);
  await signInButton.click();
}

// Wait for an email with the given subject to appear in the current view.
// Retries for up to `timeout` ms to account for delivery delay.
async function waitForEmailInInbox(page, subjectText, timeout = 60_000) {
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    // Roundcube Elastic renders emails as <tr> rows inside #messagelist tbody
    const emailRow = page.locator("#messagelist tbody tr, table.messagelist tbody tr").filter({ hasText: subjectText });

    if (await emailRow.first().isVisible().catch(() => false)) {
      return emailRow.first();
    }

    // Refresh inbox by clicking the inbox folder
    await page.getByRole("link", { name: "Inbox" }).first().click().catch(() => {});
    await page.waitForTimeout(3_000);
  }

  throw new Error(`Timed out waiting for email with subject "${subjectText}" to arrive`);
}

test.beforeEach(() => {
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set in the Playwright env file").toBeTruthy();
  expect(mailuBaseUrl,  "MAILU_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(adminUsername, "ADMIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(adminEmail,    "ADMIN_EMAIL must be set in the Playwright env file").toBeTruthy();
  expect(biberUsername, "BIBER_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(biberPassword, "BIBER_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(biberEmail,    "BIBER_EMAIL must be set in the Playwright env file").toBeTruthy();
});

// Scenario I: dashboard → click Mailu → SSO login → webinterface → admin interface → logout
test("dashboard to mailu: sso login, open admin interface, logout", async ({ page }) => {
  const expectedOidcAuthUrl  = `${oidcIssuerUrl.replace(/\/$/, "")}/protocol/openid-connect/auth`;
  const expectedMailuBaseUrl = mailuBaseUrl.replace(/\/$/, "");

  // 1. Navigate to dashboard and click Mailu app link
  await page.goto("/");
  await page.getByRole("link", { name: "Explore Mailu" }).click();

  // 2. Mailu opens in an iframe on the dashboard
  const mailuIframe = page.locator("#main iframe");
  const mailuFrame  = mailuIframe.contentFrame();

  await expect(mailuIframe).toBeVisible();

  // 3. Mailu's SSO fork may land on /sso/login before redirecting to Keycloak — click through it
  await page.waitForTimeout(2_000);
  await clickThroughMailuSsoPage(mailuFrame);

  // 4. Wait for iframe to redirect to Keycloak OIDC auth
  await expect
    .poll(
      async () => {
        const handle = await mailuIframe.elementHandle();
        const frame  = handle ? await handle.contentFrame() : null;

        return frame ? frame.url() : "";
      },
      {
        timeout: 60_000,
        message: `Expected Mailu iframe to navigate to Keycloak OIDC: ${expectedOidcAuthUrl}`
      }
    )
    .toContain(expectedOidcAuthUrl);

  // 5. Fill credentials and sign in via Keycloak
  await performOidcLogin(mailuFrame, adminUsername, adminPassword);

  // 6. Wait for redirect back to Mailu webmail
  await expect
    .poll(
      async () => {
        const handle = await mailuIframe.elementHandle();
        const frame  = handle ? await handle.contentFrame() : null;

        return frame ? frame.url() : "";
      },
      {
        timeout: 60_000,
        message: `Expected Mailu iframe to redirect back to Mailu after login: ${expectedMailuBaseUrl}`
      }
    )
    .toContain(expectedMailuBaseUrl);

  // 6. Verify logged in — look for compose button or inbox folder link
  const composeButton  = mailuFrame.getByRole("button", { name: /compose/i });
  const inboxContainer = mailuFrame.getByRole("link", { name: /inbox/i });

  await waitForFirstVisible(page, [composeButton, inboxContainer], 30_000);

  // 7. Navigate to the admin interface (admin users see an Administration link or /admin path)
  const adminLink = mailuFrame.getByRole("link", { name: /administration|admin/i });
  const adminLinkVisible = await adminLink.first().isVisible().catch(() => false);

  if (adminLinkVisible) {
    await adminLink.first().click();
  } else {
    // Fallback: navigate directly to the admin URL
    await page.goto(`${expectedMailuBaseUrl}/admin`);
  }

  // 8. Verify admin interface loaded — match any heading visible in Mailu's admin panel
  await expect(
    page.locator("h1, h2, h3, .nav-title, .sidebar-heading").filter({ hasText: /administration|domains|user|mail/i }).first()
  ).toBeVisible({ timeout: 30_000 });

  // 9. Logout — Mailu admin logout is a link with /logout or /signout in the href
  const logoutByHref = page.locator("a[href*='logout'], a[href*='signout']");
  const logoutVisible = await logoutByHref.first().isVisible({ timeout: 5_000 }).catch(() => false);

  if (logoutVisible) {
    await logoutByHref.first().click();
  } else {
    // Fallback: navigate directly to the admin logout endpoint
    await page.goto(`${expectedMailuBaseUrl}/admin/ui/logout`);
  }
  await page.goto("/");
});

// Scenario II: biber logs in → sends email to administrator → logs out →
//              administrator logs in → waits for email → logs out
test("mailu: biber sends email to administrator, administrator receives it", async ({ page }) => {
  const expectedOidcAuthUrl = `${oidcIssuerUrl.replace(/\/$/, "")}/protocol/openid-connect/auth`;
  const testSubject         = `Playwright test ${Date.now()}`;

  // --- Part 1: biber logs in and sends email ---

  await page.goto(mailuBaseUrl);

  // Mailu webmail may show an SSO button or redirect directly to Keycloak
  const ssoButton = page.getByRole("button", { name: /sso|single sign.?on|login with/i });
  const ssoButtonVisible = await ssoButton.first().isVisible({ timeout: 5_000 }).catch(() => false);

  if (ssoButtonVisible) {
    await ssoButton.first().click();
  }

  // Click through Mailu's own /sso/login intermediate page if present
  await clickThroughMailuSsoPage(page);

  // Wait for Keycloak OIDC auth page
  await expect
    .poll(() => page.url(), {
      timeout: 30_000,
      message: `Expected redirect to Keycloak OIDC: ${expectedOidcAuthUrl}`
    })
    .toContain(expectedOidcAuthUrl);

  await performOidcLogin(page, biberUsername, biberPassword);

  // Wait for redirect back to Mailu webmail
  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: "Expected redirect back to Mailu webmail after biber login"
    })
    .toContain(mailuBaseUrl.replace(/\/$/, ""));

  // Navigate directly to Roundcube compose URL — clicking the compose button requires
  // rcmail.js to fully execute, direct navigation is more reliable in Playwright.
  // Selectors confirmed from rendered DOM: id="_to", id="compose-subject",
  // id="composebody", button.btn.btn-primary.send inside .formbuttons
  await page.goto(mailuBaseUrl.replace(/\/$/, "") + "/webmail/?_task=mail&_action=compose");
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});

  const toField      = page.locator("#_to, input[name='_to']").first();
  const subjectField = page.locator("#compose-subject, input[name='_subject']").first();
  const bodyField    = page.locator("#composebody, textarea[name='_message'], [contenteditable='true']").first();
  const sendButton   = page.locator(".formbuttons .send, button.send, a.send");

  await toField.waitFor({ state: "visible", timeout: 30_000 });
  await toField.fill(adminEmail);

  await subjectField.fill(testSubject);
  await bodyField.click();
  await bodyField.fill("Hello Administrator, this is an automated Playwright test email.");

  await sendButton.first().waitFor({ state: "visible", timeout: 10_000 });
  await sendButton.first().click();

  // After send, Roundcube redirects away from _action=compose
  await expect.poll(() => page.url(), { timeout: 30_000 })
    .not.toContain("_action=compose");

  // Logout as biber
  const biberLogoutLink = page.locator("a[href*='logout'], a[href*='signout']")
    .or(page.getByRole("button", { name: /logout/i }))
    .or(page.getByRole("link", { name: /logout/i }));

  await biberLogoutLink.first().waitFor({ state: "visible", timeout: 10_000 });
  await biberLogoutLink.first().click();

  // Keycloak 18+ shows a logout confirmation page when id_token_hint is absent.
  // Wait for it, then click through so the SSO session is actually terminated before
  // the admin login flow begins — otherwise Mailu auto-logs in the next user.
  await page.waitForLoadState("networkidle", { timeout: 20_000 }).catch(() => {});

  if (page.url().includes("openid-connect/logout")) {
    const confirmLogout = page.locator("#kc-logout, button[name='logout'], input[name='logout']")
      .or(page.getByRole("button", { name: /sign out/i }));
    if (await confirmLogout.first().isVisible({ timeout: 5_000 }).catch(() => false)) {
      await confirmLogout.first().click();
      await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
    }
  }

  // --- Part 2: administrator logs in and checks inbox ---

  await page.goto(mailuBaseUrl);

  const ssoButtonAdmin = page.getByRole("button", { name: /sso|single sign.?on|login with/i });
  const ssoAdminVisible = await ssoButtonAdmin.first().isVisible({ timeout: 5_000 }).catch(() => false);

  if (ssoAdminVisible) {
    await ssoButtonAdmin.first().click();
  }

  // Click through Mailu's own /sso/login intermediate page if present
  await clickThroughMailuSsoPage(page);

  await expect
    .poll(() => page.url(), {
      timeout: 30_000,
      message: `Expected redirect to Keycloak OIDC: ${expectedOidcAuthUrl}`
    })
    .toContain(expectedOidcAuthUrl);

  await performOidcLogin(page, adminUsername, adminPassword);

  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: "Expected redirect back to Mailu webmail after admin login"
    })
    .toContain(mailuBaseUrl.replace(/\/$/, ""));

  // Wait for inbox to load
  const inboxFolder = page.getByRole("link", { name: "Inbox" });

  await inboxFolder.first().waitFor({ state: "visible", timeout: 30_000 });
  await inboxFolder.first().click();

  // Wait for biber's email to arrive (email delivery may take a few seconds)
  const emailRow = await waitForEmailInInbox(page, testSubject, 60_000);

  await expect(emailRow).toBeVisible();
  await emailRow.click();

  // Verify email content is visible (Roundcube shows message body in #messagecontframe iframe or preview pane)
  await expect(
    page.locator("#messagecontframe, #mailview-right, .message-part").first()
  ).toBeVisible({ timeout: 15_000 });

  // Logout as administrator
  const adminLogoutLink = page.locator("a[href*='logout'], a[href*='signout']")
    .or(page.getByRole("button", { name: /logout/i }))
    .or(page.getByRole("link", { name: /logout/i }));

  await adminLogoutLink.first().waitFor({ state: "visible", timeout: 10_000 });
  await adminLogoutLink.first().click();
});
