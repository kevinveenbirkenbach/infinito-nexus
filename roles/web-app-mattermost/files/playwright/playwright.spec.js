const { test, expect } = require("@playwright/test");

const { decodeDotenvQuotedValue, performKeycloakLoginForm, runAdminFlow, runBiberFlow, runGuestFlow } = require("./personas");
const { isServiceEnabled } = require("./service-gating");
test.use({
  ignoreHTTPSErrors: true
});

const oidcEnabled = isServiceEnabled("oidc");

// `docker --env-file` preserves the quotes emitted by `dotenv_quote`,
// so normalize these values before building URLs or typing credentials.
const oidcIssuerUrl      = decodeDotenvQuotedValue(process.env.OIDC_ISSUER_URL);
const mattermostBaseUrl  = decodeDotenvQuotedValue(process.env.MATTERMOST_BASE_URL);
const adminUsername      = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword      = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const biberUsername      = decodeDotenvQuotedValue(process.env.BIBER_USERNAME);
const biberPassword      = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD);

async function waitForFirstVisible(locators, timeout = 60_000) {
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    for (const locator of locators) {
      if (await locator.first().isVisible().catch(() => false)) {
        return locator.first();
      }
    }

    await new Promise(r => setTimeout(r, 500));
  }

  throw new Error("Timed out waiting for one of the expected selectors to become visible");
}

// Perform SSO login via Keycloak inside a frame context (or page context for direct navigation).

// Trigger the Mattermost SSO flow the way a real user does: navigate to
// the login page, then click the "SSO with Infinito.Nexus" button that
// templates/javascript.js.j2 injects via MutationObserver. This verifies
// end-to-end that (a) the login form mounts, (b) the injection fires,
// (c) the rendered button carries the right href and (d) the click
// kicks off the Keycloak OIDC round-trip. Direct navigation to
// /oauth/gitlab/login would skip (a)-(c) and silently hide button
// regressions; if the user cannot click their way through, the test
// should fail.
//
// Mattermost v11 redirects fresh browser contexts (no cookies) from
// /login to /landing before the login form renders. We bounce back to
// /login until the form (#input_loginId) actually mounts, so the
// injection has an anchor.
async function startMattermostSsoFlow(page, baseUrl) {
  const base = baseUrl.replace(/\/$/, "");
  await page.goto(`${base}/login`);
  if (page.url().includes("/landing")) {
    await page.goto(`${base}/login`);
  }

  // Wait for the login form to mount before looking for the SSO button.
  // The injection's MutationObserver only fires once #input_loginId
  // exists, so racing the button query against form-mount is what
  // caused the original 30s timeouts on fresh contexts.
  await page
    .locator("#input_loginId")
    .waitFor({ state: "visible", timeout: 30_000 });

  const ssoButton = page.locator("a[href='/oauth/gitlab/login']");
  await ssoButton.waitFor({ state: "visible", timeout: 30_000 });
  await ssoButton.click();
}

// Dismiss Mattermost onboarding modals/tips that may appear after first SSO login.
async function dismissMattermostPopups(frame) {
  const dismissSelectors = [
    // Existing selectors
    frame.getByRole("button", { name: /next|done|skip|got it|close|ok/i }),
    frame.locator("[aria-label='Close'], .modal-header .close, button.close"),
    // NEW: Target the specific onboarding overlay causing the intercept error
    frame.locator("[data-cy='onboarding-task-list-overlay']"),
    frame.locator(".onboarding-tour-tip__close"),
    // "Welcome to Mattermost" onboarding card on first DM open — its
    // dismiss button reads "No thanks, I'll figure it out myself".
    frame.getByRole("button", { name: /no thanks/i }),
    frame.getByText(/no thanks, i'?ll figure it out/i),
  ];

  for (let round = 0; round < 3; round++) {
    for (const sel of dismissSelectors) {
      if (await sel.first().isVisible({ timeout: 2000 }).catch(() => false)) {
        // If it's the overlay itself, we might need to click a specific 'X' or 'Skip' inside it
        // but often clicking the element or pressing Escape works.
        await sel.first().click({ force: true }).catch(() => {});
        await new Promise(r => setTimeout(r, 500));
      }
    }

    // Forcefully hide the onboarding root if it persists via CSS 
    // (This is a 'hammer' approach if the click fails)
    await frame.evaluate(() => {
      document.querySelectorAll("[data-cy='onboarding-task-list-overlay']").forEach(el => el.remove());
      document.querySelectorAll("#root-portal").forEach(el => el.style.display = 'none');
    }).catch(() => {});

    await frame.locator("body").press("Escape").catch(() => {});
    await new Promise(r => setTimeout(r, 500));
  }
}

// Wait for Mattermost's main channel view to finish loading.
// Returns the first visible indicator (channel sidebar or Town Square link).
async function waitForMattermostChannelView(frame, timeout = 60_000) {
  const channelSidebar = frame.locator(
    ".SidebarChannel, [data-testid='channel_sidebar'], #sidebar-left, .SidebarNavContainer"
  );
  const townSquare = frame.getByText("Town Square");

  return waitForFirstVisible([channelSidebar, townSquare], timeout);
}

// Log out via the universal logout endpoint.
// Every app's nginx vhost intercepts `location = /logout` and proxies it to
// web-svc-logout, which terminates all active sessions across all apps.
// Using `waitUntil: 'commit'` avoids net::ERR_ABORTED from the multi-domain
// redirect chain the service triggers after invalidating the session.
async function mattermostLogout(page, baseUrl) {
  await page.goto(`${baseUrl.replace(/\/$/, "")}/logout`, { waitUntil: "commit" }).catch(() => {});
}

test.beforeEach(() => {
  expect(oidcIssuerUrl,     "OIDC_ISSUER_URL must be set in the Playwright env file").toBeTruthy();
  expect(mattermostBaseUrl, "MATTERMOST_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(adminUsername,     "ADMIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword,     "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(biberUsername,     "BIBER_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(biberPassword,     "BIBER_PASSWORD must be set in the Playwright env file").toBeTruthy();
});

// Scenario: Mattermost SSO login → verify channel view → logout
//
// The SSO flow runs through `startMattermostSsoFlow`, which clicks the
// "SSO with Infinito.Nexus" button injected by templates/javascript.js.j2.
// This covers both the UI (is the button rendered for the user?) and
// the OIDC plumbing (does the click trigger the Keycloak round-trip?)
// in one assertion path; a button regression fails this test before
// the OIDC code is even reached.
test("mattermost: sso login, verify channel view, logout", async ({ page }) => {
  test.skip(!oidcEnabled, "OIDC shared service disabled");
  const expectedOidcAuthUrl       = `${oidcIssuerUrl.replace(/\/$/, "")}/protocol/openid-connect/auth`;
  const expectedMattermostBaseUrl = mattermostBaseUrl.replace(/\/$/, "");

  // 1. Trigger SSO by navigating directly to the Mattermost login page and clicking SSO
  await startMattermostSsoFlow(page, expectedMattermostBaseUrl);

  // 4. Wait for redirect to Keycloak OIDC auth
  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `Expected redirect to Keycloak OIDC: ${expectedOidcAuthUrl}`
    })
    .toContain(expectedOidcAuthUrl);

  // 5. Fill credentials and sign in via Keycloak
  await performKeycloakLoginForm(page, adminUsername, adminPassword);

  // 6. Wait for redirect back to Mattermost after successful auth
  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `Expected redirect back to Mattermost: ${expectedMattermostBaseUrl}`
    })
    .toContain(expectedMattermostBaseUrl);

  // 7. Dismiss any onboarding popups that appear after first SSO login
  await dismissMattermostPopups(page);

  // 8. Verify logged in — channel sidebar or Town Square must be visible
  await waitForMattermostChannelView(page, 30_000);

  // 9. Logout via API — session is invalidated without going through the nginx /logout
  // intercept that routes to the universal-logout service.
  await mattermostLogout(page, expectedMattermostBaseUrl);

  // 10. Verify the session is gone — Mattermost should redirect to login or landing
  // for unauthenticated requests. In Mattermost v11+ the default unauthenticated
  // redirect is /landing#/ rather than /login.
  await page.goto(`${expectedMattermostBaseUrl}/`, { waitUntil: "domcontentloaded" });
  await expect
    .poll(() => page.url(), {
      timeout: 15_000,
      message: "Expected Mattermost to redirect to /login or /landing after logout"
    })
    .toMatch(/\/(login|landing)/);
});

// Scenario III: biber logs in → sends direct message to administrator → administrator logs in
//              (separate browser) → verifies message → both log out
//
// Using isolated browser contexts models two separate users on separate machines:
// no shared cookies, no shared Keycloak SSO session.
test("mattermost: biber sends direct message to administrator, administrator receives it", async ({ browser }) => {
  test.skip(!oidcEnabled, "OIDC shared service disabled");
  const expectedOidcAuthUrl       = `${oidcIssuerUrl.replace(/\/$/, "")}/protocol/openid-connect/auth`;
  const expectedMattermostBaseUrl = mattermostBaseUrl.replace(/\/$/, "");
  const testMessage               = `Playwright test ${Date.now()}`;

  // Separate contexts = separate browser profiles (no shared cookies or SSO session)
  const biberContext = await browser.newContext({ ignoreHTTPSErrors: true });
  const adminContext = await browser.newContext({ ignoreHTTPSErrors: true });

  try {
    // --- Part 1: biber logs in and sends a direct message to administrator ---

    const biberPage = await biberContext.newPage();

    // Trigger SSO directly — bypasses /landing app-selection dialog for fresh contexts
    await startMattermostSsoFlow(biberPage, expectedMattermostBaseUrl);

    // Wait for redirect to Keycloak OIDC auth page
    await expect
      .poll(() => biberPage.url(), {
        timeout: 30_000,
        message: `Expected redirect to Keycloak OIDC: ${expectedOidcAuthUrl}`
      })
      .toContain(expectedOidcAuthUrl);

    await performKeycloakLoginForm(biberPage, biberUsername, biberPassword);

    // Wait for redirect back to Mattermost (any path under the base URL)
    await expect
      .poll(() => biberPage.url(), {
        timeout: 60_000,
        message: "Expected redirect back to Mattermost after biber login"
      })
      .toContain(expectedMattermostBaseUrl);

    // Dismiss onboarding popups that appear for new SSO users
    await dismissMattermostPopups(biberPage);

    // Open DM with administrator by navigating directly to the DM URL.
    // On first login biber has no team membership and lands on /select_team —
    // navigating to /{team}/messages/@{username} auto-joins the open team and
    // opens the DM in one step, so waitForMattermostChannelView is not needed here.
    // Mattermost v11 supports /{team}/messages/@{username} — more reliable than
    // clicking the sidebar "New DM" button whose aria-label changed across versions.
    await biberPage.goto(`${expectedMattermostBaseUrl}/main/messages/@${adminUsername}`);

    // Re-dismiss popups after navigation: opening the DM channel for the
    // first time triggers the "Welcome to Mattermost" onboarding card,
    // which intercepts Enter-key submission of the post composer.
    await dismissMattermostPopups(biberPage);

    // Wait for the DM channel to open — message input must be visible
    const messageInput = biberPage
      .locator("#post_textbox, [data-testid='post_textbox'], div[contenteditable='true'].post-create__input")
      .first();

    await messageInput.waitFor({ state: "visible", timeout: 30_000 });
    await messageInput.click({ force: true });
    // Use keyboard.type() rather than fill() — Mattermost's rich-text editor is a
    // contenteditable div and fill() bypasses React's onChange handlers, leaving the
    // component state empty even though the text is visible in the DOM.
    await biberPage.keyboard.type(testMessage);

    // Send the message (Enter key submits; Shift+Enter inserts a newline)
    await biberPage.keyboard.press("Enter");

    // Confirm the message appears in the channel.
    // getByTestId('postContent') scopes to the post body, avoiding strict-mode
    // violations from Mattermost's screen-reader <span> that duplicates the text.
    await expect(biberPage.getByTestId("postContent").getByText(testMessage)).toBeVisible({ timeout: 15_000 });

    // Logout as biber
    await mattermostLogout(biberPage, expectedMattermostBaseUrl);

    // --- Part 2: administrator logs in and verifies the direct message (fresh browser context) ---

    const adminPage = await adminContext.newPage();

    // Trigger SSO directly — bypasses /landing app-selection dialog for fresh contexts
    await startMattermostSsoFlow(adminPage, expectedMattermostBaseUrl);

    await expect
      .poll(() => adminPage.url(), {
        timeout: 30_000,
        message: `Expected redirect to Keycloak OIDC: ${expectedOidcAuthUrl}`
      })
      .toContain(expectedOidcAuthUrl);

    await performKeycloakLoginForm(adminPage, adminUsername, adminPassword);

    await expect
      .poll(() => adminPage.url(), {
        timeout: 60_000,
        message: "Expected redirect back to Mattermost after admin login"
      })
      .toContain(expectedMattermostBaseUrl);

    await dismissMattermostPopups(adminPage);
    await waitForMattermostChannelView(adminPage, 30_000);

    // Open DM with biber by navigating directly to the DM URL.
    await adminPage.goto(`${expectedMattermostBaseUrl}/main/messages/@${biberUsername}`);

    // Verify biber's message is visible in the DM channel
    await expect(adminPage.getByTestId("postContent").getByText(testMessage)).toBeVisible({ timeout: 30_000 });

    // Logout as administrator
    await mattermostLogout(adminPage, expectedMattermostBaseUrl);

  } finally {
    await biberContext.close().catch(() => {});
    await adminContext.close().catch(() => {});
  }
});

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
  await runAdminFlow(page, {
    adminInteraction: async (interactivePage) => {
      // web-app-mattermost admin-only interaction: open a management surface.
      const link = interactivePage
        .getByRole("link", { name: /^(system console|admin|workspaces|teams|channels)$/i })
        .first();
      if (await link.isVisible({ timeout: 10_000 }).catch(() => false)) {
        await link.click().catch(() => {});
        await interactivePage.waitForLoadState("domcontentloaded", { timeout: 30_000 }).catch(() => {});
        await expect(interactivePage.locator("body")).toContainText(
          /system console|workspace|teams|channels|users|reporting/i,
          { timeout: 30_000 },
        );
      }
    },
  });
});
