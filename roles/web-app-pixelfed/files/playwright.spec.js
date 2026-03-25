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

const loginUsername = decodeDotenvQuotedValue(process.env.LOGIN_USERNAME);
const loginPassword = decodeDotenvQuotedValue(process.env.LOGIN_PASSWORD);
const oidcIssuerUrl = decodeDotenvQuotedValue(process.env.OIDC_ISSUER_URL);
const pixelfedBaseUrl = decodeDotenvQuotedValue(process.env.PIXELFED_BASE_URL);

async function waitForFirstVisible(page, locators, timeout = 60_000, errorMessage = "Timed out waiting for a visible locator") {
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    for (const locator of locators) {
      const candidate = locator.first();

      if (await candidate.isVisible().catch(() => false)) {
        return candidate;
      }
    }

    await page.waitForTimeout(500);
  }

  throw new Error(errorMessage);
}

async function findFirstVisibleCandidate(candidates) {
  for (const candidate of candidates) {
    const locator = candidate.locator.first();

    if (await locator.isVisible().catch(() => false)) {
      return { ...candidate, locator };
    }
  }

  return null;
}

async function waitForVisibleCandidate(
  page,
  candidates,
  timeout = 60_000,
  errorMessage = "Timed out waiting for a visible candidate"
) {
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    const visibleCandidate = await findFirstVisibleCandidate(candidates);

    if (visibleCandidate) {
      return visibleCandidate;
    }

    await page.waitForTimeout(500);
  }

  throw new Error(errorMessage);
}

async function getIframeUrl(iframeLocator) {
  const iframeHandle = await iframeLocator.elementHandle();
  const iframeFrame = iframeHandle ? await iframeHandle.contentFrame() : null;

  return iframeFrame ? iframeFrame.url() : "";
}

async function waitForIframeUrl(page, iframeLocator, predicate, timeout = 60_000, errorMessage) {
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    const iframeUrl = await getIframeUrl(iframeLocator);

    if (predicate(iframeUrl)) {
      return iframeUrl;
    }

    await page.waitForTimeout(500);
  }

  throw new Error(errorMessage || "Timed out waiting for iframe URL to match the expected state");
}

async function anyVisible(locators) {
  for (const locator of locators) {
    if (await locator.first().isVisible().catch(() => false)) {
      return true;
    }
  }

  return false;
}

test.beforeEach(() => {
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set in the Playwright env file").toBeTruthy();
  expect(pixelfedBaseUrl, "PIXELFED_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(loginUsername, "LOGIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(loginPassword, "LOGIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
});

test("dashboard to pixelfed oidc login", async ({ page }) => {
  const expectedOidcAuthUrl = `${oidcIssuerUrl.replace(/\/$/, "")}/protocol/openid-connect/auth`;
  const expectedPixelfedBaseUrl = pixelfedBaseUrl.replace(/\/$/, "");

  await page.goto("/");

  const pixelfedEntry = await waitForFirstVisible(
    page,
    [
      page.getByRole("link", { name: "Explore Pixelfed" }),
      page.getByRole("link", { name: /^Pixelfed$/i })
    ],
    60_000,
    "Timed out waiting for the Pixelfed entry on the dashboard"
  );

  await pixelfedEntry.click();

  const pixelfedIframe = page.locator("#main iframe");
  const pixelfedFrame = pixelfedIframe.contentFrame();
  const usernameField = pixelfedFrame.locator('input[name="username"], input#username, input[type="email"]');
  const passwordField = pixelfedFrame.locator('input[name="password"], input#password, input[type="password"]');
  const signInButton = pixelfedFrame.locator('button[type="submit"], input[type="submit"]');
  const rememberMeCheckbox = pixelfedFrame.locator('input[name="rememberMe"], input#rememberMe');
  const pixelfedLoginEntryCandidates = [
    {
      kind: "login-link",
      locator: pixelfedFrame.getByRole("link", { name: /^Login$/i })
    },
    {
      kind: "login-href",
      locator: pixelfedFrame.locator('a[href="/login"], a[title="Login"]')
    }
  ];
  const pixelfedOidcEntryCandidates = [
    {
      kind: "oidc-link",
      locator: pixelfedFrame.getByRole("link", { name: /^Sign-in with OIDC$/i })
    },
    {
      kind: "oidc-href",
      locator: pixelfedFrame.locator('a[href="/auth/oidc/start"]')
    }
  ];
  const pixelfedAuthenticatedCandidates = [
    {
      kind: "user-menu",
      locator: pixelfedFrame.getByRole("link", { name: /^User Menu$/i })
    },
    {
      kind: "user-menu-title",
      locator: pixelfedFrame.locator('a[title="User Menu"], a[aria-haspopup="true"]')
    },
    {
      kind: "settings",
      locator: pixelfedFrame.locator('a[href="/settings/home"], a[href*="/settings/home"]')
    },
    {
      kind: "logout",
      locator: pixelfedFrame.locator('a[href="/logout"], a[href*="/logout"]')
    }
  ];
  const dashboardAccountCandidates = [
    page.getByRole("link", { name: /^Account$/i }),
    page.getByRole("button", { name: /^Account$/i }),
    page.locator("nav").getByText(/^Account$/i)
  ];
  const dashboardLogoutCandidates = [
    page.getByRole("link", { name: /^Logout$/i }),
    page.getByRole("button", { name: /^Logout$/i }),
    page.locator("nav").getByText(/^Logout$/i)
  ];
  const dashboardLoginCandidates = [
    page.getByRole("link", { name: /^Login$/i }),
    page.getByRole("button", { name: /^Login$/i }),
    page.locator("nav").getByText(/^Login$/i)
  ];

  await expect(pixelfedIframe).toBeVisible();

  await waitForIframeUrl(
    page,
    pixelfedIframe,
    (url) => url.includes(expectedOidcAuthUrl) || url.includes(expectedPixelfedBaseUrl),
    60_000,
    `Expected Pixelfed iframe to load either Pixelfed or the Keycloak OIDC endpoint: ${expectedOidcAuthUrl}`
  );

  if (!(await getIframeUrl(pixelfedIframe)).includes(expectedOidcAuthUrl)) {
    const pixelfedOidcEntry = await waitForVisibleCandidate(
      page,
      pixelfedOidcEntryCandidates,
      5_000
    ).catch(() => null);

    if (!pixelfedOidcEntry) {
      const pixelfedLoginEntry = await waitForVisibleCandidate(
        page,
        pixelfedLoginEntryCandidates,
        20_000,
        "Timed out waiting for the Pixelfed login entry before starting the OIDC flow"
      );

      await pixelfedLoginEntry.locator.click();
    }

    const oidcStartEntry = pixelfedOidcEntry || await waitForVisibleCandidate(
      page,
      pixelfedOidcEntryCandidates,
      20_000,
      "Timed out waiting for the Pixelfed 'Sign-in with OIDC' action"
    );

    await oidcStartEntry.locator.click();

    await waitForIframeUrl(
      page,
      pixelfedIframe,
      (url) => url.includes(expectedOidcAuthUrl),
      60_000,
      `Expected Pixelfed iframe to navigate to Keycloak via Pixelfed's OIDC entry point: ${expectedOidcAuthUrl}`
    );
  }

  const visibleUsernameField = await waitForFirstVisible(
    page,
    [usernameField, pixelfedFrame.getByRole("textbox", { name: /username|email/i })],
    60_000,
    "Timed out waiting for the Keycloak username field in the Pixelfed iframe"
  );

  await expect(visibleUsernameField).toBeVisible();
  await visibleUsernameField.click();
  await visibleUsernameField.fill(loginUsername);
  await passwordField.first().fill(loginPassword);

  if (await rememberMeCheckbox.first().isVisible().catch(() => false)) {
    await rememberMeCheckbox.first().check().catch(() => {});
  } else {
    await pixelfedFrame.getByText(/remember me/i).click({ timeout: 2_000 }).catch(() => {});
  }

  const visibleSignInButton = await waitForFirstVisible(
    page,
    [signInButton, pixelfedFrame.getByRole("button", { name: /sign in|log in|login/i })],
    30_000,
    "Timed out waiting for the Keycloak sign-in button in the Pixelfed iframe"
  );

  await visibleSignInButton.click();

  await waitForIframeUrl(
    page,
    pixelfedIframe,
    (url) => url.includes(expectedPixelfedBaseUrl) && !url.includes(expectedOidcAuthUrl),
    60_000,
    `Expected Pixelfed iframe to redirect back to Pixelfed after Keycloak login: ${expectedPixelfedBaseUrl}`
  );

  const authenticatedState = await waitForVisibleCandidate(
    page,
    pixelfedAuthenticatedCandidates,
    60_000,
    "Timed out waiting for an authenticated Pixelfed UI after the Keycloak login redirect"
  );

  await expect(authenticatedState.locator).toBeVisible();

  // Reload the dashboard after the iframe login so the parent page refreshes its Keycloak session state.
  await page.goto("/");

  const accountTrigger = await waitForFirstVisible(
    page,
    dashboardAccountCandidates,
    60_000,
    "Timed out waiting for the dashboard Account menu after the Pixelfed login"
  );

  await accountTrigger.click();

  const logoutTrigger = await waitForFirstVisible(
    page,
    dashboardLogoutCandidates,
    15_000,
    "Timed out waiting for the dashboard Logout action after opening Account"
  );

  await logoutTrigger.click();

  await expect
    .poll(
      async () => {
        const loginVisible = await anyVisible(dashboardLoginCandidates);
        const accountVisible = await anyVisible(dashboardAccountCandidates);

        return loginVisible && !accountVisible;
      },
      {
        timeout: 60_000,
        message: "Expected the dashboard to return to a logged-out state after the Pixelfed OIDC logout"
      }
    )
    .toBe(true);
});
