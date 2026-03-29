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

const oidcIssuerUrl = decodeDotenvQuotedValue(process.env.OIDC_ISSUER_URL);
const pixelfedBaseUrl = decodeDotenvQuotedValue(process.env.PIXELFED_BASE_URL);
const loginScenarios = [
  {
    envSuffix: "FIRST",
    label: "biber",
    username: decodeDotenvQuotedValue(process.env.LOGIN_USERNAME_FIRST),
    password: decodeDotenvQuotedValue(process.env.LOGIN_PASSWORD_FIRST)
  },
  {
    envSuffix: "SECOND",
    label: "administrator",
    username: decodeDotenvQuotedValue(process.env.LOGIN_USERNAME_SECOND),
    password: decodeDotenvQuotedValue(process.env.LOGIN_PASSWORD_SECOND)
  }
];

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

async function getIframeHandle(page) {
  const iframe = page.locator("#main iframe").first();
  const handle = await iframe.elementHandle().catch(() => null);
  return handle;
}

async function getIframeFrame(page) {
  const handle = await getIframeHandle(page);
  return handle ? await handle.contentFrame().catch(() => null) : null;
}

async function getIframeUrl(page) {
  const frame = await getIframeFrame(page);
  return frame ? frame.url() : "";
}

async function waitForIframeUrl(page, predicate, timeout = 60_000, errorMessage) {
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    const iframeUrl = await getIframeUrl(page);

    if (predicate(iframeUrl)) {
      return iframeUrl;
    }

    await page.waitForTimeout(500);
  }

  throw new Error(errorMessage || "Timed out waiting for iframe URL to match the expected state");
}

async function anyVisible(locators) {
  for (const candidate of locators) {
    const locator = candidate.locator || candidate;
    const visibleLocator = typeof locator.first === "function" ? locator.first() : locator;

    if (await visibleLocator.isVisible().catch(() => false)) {
      return true;
    }
  }

  return false;
}

function getPixelfedLoginEntryCandidates(frame) {
  return [
    {
      kind: "login-link",
      locator: frame.getByRole("link", { name: /^Login$/i })
    },
    {
      kind: "login-button",
      locator: frame.getByRole("button", { name: /^Login$/i })
    },
    {
      kind: "login-href",
      locator: frame.locator('a[href="/login"], a[title="Login"]')
    }
  ];
}

function getPixelfedOidcEntryCandidates(frame) {
  return [
    {
      kind: "oidc-link",
      locator: frame.getByRole("link", { name: /^Sign-in with OIDC$/i })
    },
    {
      kind: "oidc-button",
      locator: frame.getByRole("button", { name: /^Sign-in with OIDC$/i })
    },
    {
      kind: "oidc-href",
      locator: frame.locator('a[href="/auth/oidc/start"]')
    }
  ];
}

function getPixelfedAuthenticatedCandidates(frame) {
  return [
    {
      kind: "user-menu",
      locator: frame.getByRole("link", { name: /^User Menu$/i })
    },
    {
      kind: "user-menu-button",
      locator: frame.getByRole("button", { name: /^User Menu$/i })
    },
    {
      kind: "user-menu-title",
      locator: frame.locator('a[title="User Menu"], a[aria-haspopup="true"]')
    },
    {
      kind: "settings",
      locator: frame.locator('a[href="/settings/home"], a[href*="/settings/home"]')
    },
    {
      kind: "logout",
      locator: frame.locator('a[href="/logout"], a[href*="/logout"]')
    },
    {
      kind: "logout-button",
      locator: frame.getByRole("button", { name: /^Logout$/i })
    }
  ];
}

function getPixelfedUserMenuCandidates(frame) {
  return getPixelfedAuthenticatedCandidates(frame).filter((candidate) =>
    ["user-menu", "user-menu-button", "user-menu-title"].includes(candidate.kind)
  );
}

function getPixelfedLogoutCandidates(frame) {
  return getPixelfedAuthenticatedCandidates(frame).filter((candidate) =>
    ["logout", "logout-button"].includes(candidate.kind)
  );
}

function getKeycloakLogoutConfirmCandidates(frame) {
  return [
    {
      kind: "kc-logout-button",
      locator: frame.getByRole("button", { name: /^Logout$/i })
    },
    {
      kind: "kc-logout-submit",
      locator: frame.locator('button[type="submit"], input[type="submit"]')
    },
    {
      kind: "kc-logout-form",
      locator: frame.locator('form button, form input[type="submit"]')
    }
  ];
}

function getLoggedOutSuccessCandidates(frame) {
  return [
    {
      kind: "logged-out-heading",
      locator: frame.getByRole("heading", { name: /you are logged out/i })
    },
    {
      kind: "logged-out-text",
      locator: frame.getByText(/you are logged out/i)
    },
    {
      kind: "session-ended-text",
      locator: frame.getByText(/logged out|session ended|signed out/i)
    }
  ];
}

async function loginToPixelfedViaDashboard(page, loginScenario) {
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
    `Timed out waiting for the Pixelfed entry on the dashboard for ${loginScenario.label}`
  );

  await pixelfedEntry.click();

  const pixelfedIframe = page.locator("#main iframe").first();
  const pixelfedFrame = await pixelfedIframe.contentFrame();
  const usernameField = pixelfedFrame.locator('input[name="username"], input#username, input[type="email"]');
  const passwordField = pixelfedFrame.locator('input[name="password"], input#password, input[type="password"]');
  const signInButton = pixelfedFrame.locator('button[type="submit"], input[type="submit"]');
  const rememberMeCheckbox = pixelfedFrame.locator('input[name="rememberMe"], input#rememberMe');
  const pixelfedLoginEntryCandidates = getPixelfedLoginEntryCandidates(pixelfedFrame);
  const pixelfedOidcEntryCandidates = getPixelfedOidcEntryCandidates(pixelfedFrame);
  const pixelfedAuthenticatedCandidates = getPixelfedAuthenticatedCandidates(pixelfedFrame);

  await expect(pixelfedIframe).toBeVisible();

  await waitForIframeUrl(
    page,
    (url) => url.includes(expectedOidcAuthUrl) || url.includes(expectedPixelfedBaseUrl),
    60_000,
    `Expected the Pixelfed iframe to load Pixelfed or Keycloak for ${loginScenario.label}: ${expectedOidcAuthUrl}`
  );

  if (!(await getIframeUrl(page)).includes(expectedOidcAuthUrl)) {
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
        `Timed out waiting for the Pixelfed login entry before starting the OIDC flow for ${loginScenario.label}`
      );

      await pixelfedLoginEntry.locator.click();
    }

    const oidcStartEntry = pixelfedOidcEntry || await waitForVisibleCandidate(
      page,
      pixelfedOidcEntryCandidates,
      20_000,
      `Timed out waiting for the Pixelfed OIDC action for ${loginScenario.label}`
    );

    await oidcStartEntry.locator.click();

    await waitForIframeUrl(
      page,
      (url) => url.includes(expectedOidcAuthUrl),
      60_000,
      `Expected the Pixelfed iframe to navigate to Keycloak for ${loginScenario.label}: ${expectedOidcAuthUrl}`
    );
  }

  const visibleUsernameField = await waitForFirstVisible(
    page,
    [usernameField, pixelfedFrame.getByRole("textbox", { name: /username|email/i })],
    60_000,
    `Timed out waiting for the Keycloak username field in the Pixelfed iframe for ${loginScenario.label}`
  );

  await expect(visibleUsernameField).toBeVisible();
  await visibleUsernameField.click();
  await visibleUsernameField.fill(loginScenario.username);
  await passwordField.first().fill(loginScenario.password);

  if (await rememberMeCheckbox.first().isVisible().catch(() => false)) {
    await rememberMeCheckbox.first().check().catch(() => {});
  } else {
    await pixelfedFrame.getByText(/remember me/i).click({ timeout: 2_000 }).catch(() => {});
  }

  const visibleSignInButton = await waitForFirstVisible(
    page,
    [signInButton, pixelfedFrame.getByRole("button", { name: /sign in|log in|login/i })],
    30_000,
    `Timed out waiting for the Keycloak sign-in button in the Pixelfed iframe for ${loginScenario.label}`
  );

  await visibleSignInButton.click();

  await waitForIframeUrl(
    page,
    (url) => url.includes(expectedPixelfedBaseUrl) && !url.includes(expectedOidcAuthUrl),
    60_000,
    `Expected the Pixelfed iframe to redirect back to Pixelfed after Keycloak login for ${loginScenario.label}: ${expectedPixelfedBaseUrl}`
  );

  const authenticatedState = await waitForVisibleCandidate(
    page,
    pixelfedAuthenticatedCandidates,
    60_000,
    `Timed out waiting for an authenticated Pixelfed UI after the Keycloak login redirect for ${loginScenario.label}`
  );

  await expect(authenticatedState.locator).toBeVisible();
}

async function confirmKeycloakLogoutIfNeeded(page, loginScenario) {
  const expectedOidcLogoutIndicator = "/protocol/openid-connect/logout";
  const deadline = Date.now() + 20_000;

  while (Date.now() < deadline) {
    const frame = await getIframeFrame(page);
    if (!frame) {
      await page.waitForTimeout(500);
      continue;
    }

    const keycloakLogoutConfirmCandidates = getKeycloakLogoutConfirmCandidates(frame);
    const iframeUrl = await getIframeUrl(page);
    const looksLikeKeycloakLogout = iframeUrl.includes(expectedOidcLogoutIndicator);

    const visibleConfirm = await waitForVisibleCandidate(
      page,
      keycloakLogoutConfirmCandidates,
      2_000,
      `Timed out waiting for the Keycloak logout confirmation button for ${loginScenario.label}`
    ).catch(() => null);

    if (looksLikeKeycloakLogout || visibleConfirm) {
      const confirmButton = visibleConfirm || await waitForVisibleCandidate(
        page,
        keycloakLogoutConfirmCandidates,
        5_000,
        `Timed out waiting for the Keycloak logout confirmation button for ${loginScenario.label}`
      );

      await confirmButton.locator.click().catch(() => {});
      return true;
    }

    const loggedOutSuccessVisible = await anyVisible(getLoggedOutSuccessCandidates(frame));
    const pixelfedLoginVisible = await anyVisible(getPixelfedLoginEntryCandidates(frame));

    if (loggedOutSuccessVisible || pixelfedLoginVisible) {
      return false;
    }

    await page.waitForTimeout(500);
  }

  return false;
}

async function logoutFromPixelfed(page, loginScenario) {
  const expectedOidcAuthUrl = `${oidcIssuerUrl.replace(/\/$/, "")}/protocol/openid-connect/auth`;

  const pixelfedIframe = page.locator("#main iframe").first();
  const pixelfedFrame = await pixelfedIframe.contentFrame();
  const pixelfedUserMenuCandidates = getPixelfedUserMenuCandidates(pixelfedFrame);
  const pixelfedLogoutCandidates = getPixelfedLogoutCandidates(pixelfedFrame);

  await expect(pixelfedIframe).toBeVisible();

  let logoutTrigger = await waitForVisibleCandidate(
    page,
    pixelfedLogoutCandidates,
    10_000,
    `Timed out waiting for the Pixelfed Logout action after login for ${loginScenario.label}`
  ).catch(() => null);

  if (!logoutTrigger) {
    const userMenuTrigger = await waitForVisibleCandidate(
      page,
      pixelfedUserMenuCandidates,
      10_000,
      `Timed out waiting for the Pixelfed User Menu after login for ${loginScenario.label}`
    );

    await userMenuTrigger.locator.click();

    logoutTrigger = await waitForVisibleCandidate(
      page,
      pixelfedLogoutCandidates,
      10_000,
      `Timed out waiting for the Pixelfed Logout action after opening the User Menu for ${loginScenario.label}`
    );
  }

  await logoutTrigger.locator.click();

  await confirmKeycloakLogoutIfNeeded(page, loginScenario).catch(() => false);

  await expect
    .poll(
      async () => {
        const dashboardLoginVisible = await page.getByRole("link", { name: /^Login$/i }).first().isVisible().catch(() => false);

        const frame = await getIframeFrame(page);
        if (!frame) {
          return false;
        }

        const loginCandidates = getPixelfedLoginEntryCandidates(frame);
        const logoutCandidates = getPixelfedLogoutCandidates(frame);
        const loggedOutSuccessCandidates = getLoggedOutSuccessCandidates(frame);
        const currentIframeUrl = await getIframeUrl(page);

        const pixelfedLoginVisible = await anyVisible(loginCandidates);
        const pixelfedLogoutVisible = await anyVisible(logoutCandidates);
        const loggedOutSuccessVisible = await anyVisible(loggedOutSuccessCandidates);
        const backOnLoginProvider = currentIframeUrl.includes(expectedOidcAuthUrl);

        const loggedOutStateReached =
          dashboardLoginVisible ||
          pixelfedLoginVisible ||
          loggedOutSuccessVisible ||
          backOnLoginProvider;

        return loggedOutStateReached && !pixelfedLogoutVisible;
      },
      {
        timeout: 60_000,
        message: `Expected Pixelfed to return to a logged-out state after logout for ${loginScenario.label}`
      }
    )
    .toBe(true);
}

test.beforeEach(() => {
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set in the Playwright env file").toBeTruthy();
  expect(pixelfedBaseUrl, "PIXELFED_BASE_URL must be set in the Playwright env file").toBeTruthy();

  for (const loginScenario of loginScenarios) {
    expect(
      loginScenario.username,
      `LOGIN_USERNAME_${loginScenario.envSuffix} must be set in the Playwright env file`
    ).toBeTruthy();
    expect(
      loginScenario.password,
      `LOGIN_PASSWORD_${loginScenario.envSuffix} must be set in the Playwright env file`
    ).toBeTruthy();
  }
});

for (const loginScenario of loginScenarios) {
  test(`dashboard to pixelfed oidc login (${loginScenario.label})`, async ({ page }) => {
    await loginToPixelfedViaDashboard(page, loginScenario);
    await logoutFromPixelfed(page, loginScenario);
  });
}
