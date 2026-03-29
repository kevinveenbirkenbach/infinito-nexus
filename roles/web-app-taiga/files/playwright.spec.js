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
const oidcButtonText = decodeDotenvQuotedValue(process.env.OIDC_BUTTON_TEXT);
const taigaBaseUrl = decodeDotenvQuotedValue(process.env.TAIGA_BASE_URL);
const taigaOauth2Enabled = /^(1|true|yes|on)$/i.test(process.env.TAIGA_OAUTH2_ENABLED || "");
const taigaOidcEnabled = /^(1|true|yes|on)$/i.test(process.env.TAIGA_OIDC_ENABLED || "");

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function isVisible(locator) {
  return locator.first().isVisible().catch(() => false);
}

async function findFirstVisible(locators) {
  for (const locator of locators) {
    const candidate = locator.first();

    if (await candidate.isVisible().catch(() => false)) {
      return candidate;
    }
  }

  return null;
}

async function getOauth2ProxyCookies(page, baseUrl) {
  const cookies = await page.context().cookies(baseUrl);
  return cookies.filter((cookie) => /oauth2/i.test(cookie.name));
}

function getOidcEntryLocators(target) {
  const oidcLabelPattern = oidcButtonText
    ? new RegExp(escapeRegex(oidcButtonText), "i")
    : /oidc|single sign-on|sso/i;

  return [
    target.getByRole("link", { name: oidcLabelPattern }),
    target.getByRole("button", { name: oidcLabelPattern }),
    target.locator('[href*="/oidc"], [data-href*="/oidc"], [ui-sref*="oidc"], [ng-click*="oidc"]')
  ];
}

async function waitForFrameUrl(iframeLocator, matcher, timeout, errorMessage) {
  await expect
    .poll(
      async () => {
        const iframeHandle = await iframeLocator.elementHandle();
        const frame = iframeHandle ? await iframeHandle.contentFrame() : null;
        return frame ? frame.url() : "";
      },
      {
        timeout,
        message: errorMessage
      }
    )
    .toContain(matcher);
}

async function waitForInitialTaigaAuthState(
  page,
  iframeLocator,
  taigaFrame,
  expectedTaigaBaseUrl,
  expectedOidcAuthUrl,
  timeout,
  errorMessage
) {
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    const iframeHandle = await iframeLocator.elementHandle();
    const frame = iframeHandle ? await iframeHandle.contentFrame() : null;
    const frameUrl = frame ? frame.url() : "";

    if (frameUrl.includes(expectedOidcAuthUrl)) {
      return { kind: "keycloak" };
    }

    if (frameUrl.includes(expectedTaigaBaseUrl)) {
      const oidcEntry = await findFirstVisible(getOidcEntryLocators(taigaFrame));

      if (oidcEntry) {
        return { kind: "taiga-oidc-entry", locator: oidcEntry };
      }

      const loginEntry = await findFirstVisible([
        taigaFrame.getByRole("link", { name: /^Login$/i }),
        taigaFrame.getByRole("button", { name: /^Login$/i })
      ]);

      if (loginEntry) {
        await loginEntry.click();
        await page.waitForTimeout(500);
      }
    }

    await page.waitForTimeout(500);
  }

  throw new Error(errorMessage);
}

async function waitForOauth2ProxyCookie(page, baseUrl, shouldExist, timeout, errorMessage) {
  await expect
    .poll(
      async () => {
        const oauth2Cookies = await getOauth2ProxyCookies(page, baseUrl);
        return oauth2Cookies.length > 0;
      },
      {
        timeout,
        message: errorMessage
      }
    )
    .toBe(shouldExist);
}

async function logoutFromDashboardIfNeeded(page) {
  const nav = page.locator("nav");
  const loginItem = page.locator("nav").getByText("Login", { exact: true });
  const logoutItem = page.locator("nav").getByText("Logout", { exact: true });
  const accountMenuTriggerLocators = [
    nav.locator("button"),
    nav.locator("[aria-haspopup='true']"),
    nav.getByRole("button")
  ];

  await expect
    .poll(
      async () =>
        (await isVisible(loginItem)) ||
        (await isVisible(logoutItem)) ||
        (await findFirstVisible(accountMenuTriggerLocators).then(Boolean)),
      {
        timeout: 60_000,
        message: "Expected dashboard to expose either the authenticated account menu or the Login entry after the Taiga flow"
      }
    )
    .toBe(true);

  if (await isVisible(loginItem) && !(await isVisible(logoutItem))) {
    return;
  }

  if (await isVisible(logoutItem)) {
    await logoutItem.first().click();
    await page.waitForTimeout(1_000);
  } else {
    const accountTrigger = await findFirstVisible(accountMenuTriggerLocators);

    if (!accountTrigger) {
      throw new Error(
        "Expected dashboard to expose a visible account menu trigger or Logout entry after the Taiga flow"
      );
    }

    await accountTrigger.click();
    await expect(logoutItem.first()).toBeVisible({ timeout: 10_000 });
    await logoutItem.first().click();
    await page.waitForTimeout(1_000);
  }

  await expect
    .poll(
      async () => (await isVisible(loginItem)) && !(await isVisible(logoutItem)),
      {
        timeout: 60_000,
        message: "Expected dashboard to show the Login entry again after logout"
      }
    )
    .toBe(true);
}

async function activateLocatorClick(locator) {
  const target = locator.first();
  const count = await target.count().catch(() => 0);

  if (!count) {
    return false;
  }

  try {
    await target.dispatchEvent("click");
  } catch {
    await target.evaluate((el) => el.click());
  }

  return true;
}

async function tryLogoutFromTaiga(page, taigaFrame) {
  const directLogoutLocators = [
    taigaFrame.locator('a[title="Logout"]'),
    taigaFrame.locator('a[ng-click*="logout"]'),
    taigaFrame.locator('a[href*="logout"]'),
    taigaFrame.locator('[tg-nav*="logout"]'),
    taigaFrame.getByRole("link", { name: /log ?out/i }),
    taigaFrame.getByRole("button", { name: /log ?out/i }),
    taigaFrame.locator('[href*="logout"], [ui-sref*="logout"], [ng-click*="logout"]')
  ];
  const menuTriggerLocators = [
    taigaFrame.locator("[aria-haspopup='true']"),
    taigaFrame.locator("nav button"),
    taigaFrame.locator(".user-avatar, .avatar, .profile-avatar, .profile-button, [class*='avatar']")
  ];

  for (const directLogoutLocator of directLogoutLocators) {
    if (await activateLocatorClick(directLogoutLocator)) {
      await page.waitForTimeout(1_000);
      return true;
    }
  }

  const directLogout = await findFirstVisible(directLogoutLocators);
  if (directLogout) {
    await directLogout.click({ timeout: 2_000 }).catch(() => {});
    await page.waitForTimeout(1_000);
    return true;
  }

  for (const triggerLocator of menuTriggerLocators) {
    const trigger = await findFirstVisible([triggerLocator]);

    if (!trigger) {
      continue;
    }

    await trigger.click({ timeout: 2_000 }).catch(() => {});
    await page.waitForTimeout(500);

    const revealedLogout = await findFirstVisible(directLogoutLocators);
    if (revealedLogout) {
      await revealedLogout.click({ timeout: 2_000 }).catch(() => {});
      await page.waitForTimeout(1_000);
      return true;
    }
  }

  return false;
}

async function waitForAuthenticatedTaigaShell(frameOrPage, timeout, errorMessage) {
  await expect
    .poll(
      async () => {
        const bodyText = await frameOrPage.locator("body").innerText().catch(() => "");
        const loginFormVisible = await frameOrPage
          .locator("input[name='username'], input#username, input[name='password'], input#password, #kc-login")
          .first()
          .isVisible()
          .catch(() => false);

        if (loginFormVisible) {
          return false;
        }

        return bodyText.length > 100 && /taiga|projects|kanban|backlog|discover/i.test(bodyText);
      },
      {
        timeout,
        message: errorMessage
      }
    )
    .toBe(true);
}

async function waitForTopLevelLoginRequirement(
  page,
  expectedTaigaBaseUrl,
  expectedOidcAuthUrl,
  timeout,
  errorMessage
) {
  const deadline = Date.now() + timeout;
  const keycloakUsernameField = page.locator("input[name='username'], input#username");

  while (Date.now() < deadline) {
    const currentUrl = page.url();

    if (
      currentUrl.includes(expectedOidcAuthUrl) &&
      (await keycloakUsernameField.first().isVisible().catch(() => false))
    ) {
      return { kind: "keycloak" };
    }

    if (currentUrl.includes(expectedTaigaBaseUrl)) {
      const loginEntry = await findFirstVisible([
        page.getByRole("link", { name: /^Login$/i }),
        page.getByRole("button", { name: /^Login$/i })
      ]);

      if (loginEntry) {
        return { kind: "taiga-login-page", locator: loginEntry };
      }

      const oidcEntry = await findFirstVisible(getOidcEntryLocators(page));

      if (oidcEntry) {
        return { kind: "taiga-oidc-entry", locator: oidcEntry };
      }
    }

    await page.waitForTimeout(500);
  }

  throw new Error(errorMessage);
}

function getTaigaUrls() {
  const expectedTaigaBaseUrl = taigaBaseUrl.replace(/\/$/, "");
  const expectedOidcAuthUrl = oidcIssuerUrl
    ? `${oidcIssuerUrl.replace(/\/$/, "")}/protocol/openid-connect/auth`
    : "";

  return {
    expectedTaigaBaseUrl,
    expectedOidcAuthUrl,
    taigaOauth2SignOutUrl: `${expectedTaigaBaseUrl}/oauth2/sign_out`,
    discoverUrl: `${expectedTaigaBaseUrl}/discover`,
    projectsUrl: `${expectedTaigaBaseUrl}/projects`,
    userSettingsUrl: `${expectedTaigaBaseUrl}/user-settings/user-profile`
  };
}

async function getComputedStyleValue(locator, propertyName) {
  return locator
    .first()
    .evaluate((element, cssProperty) => getComputedStyle(element).getPropertyValue(cssProperty), propertyName);
}

async function expectGradientBackground(locator, message) {
  await expect(locator.first()).toBeVisible({ timeout: 60_000 });
  await expect
    .poll(
      async () => getComputedStyleValue(locator, "background-image"),
      {
        timeout: 60_000,
        message
      }
    )
    .toMatch(/gradient/i);
}

async function loginToTaigaFromDashboard(page) {
  const taigaUrls = getTaigaUrls();
  const taigaCardLink = page.getByRole("link", { name: "Explore Taiga" });
  const taigaIframe = page.locator("#main iframe");

  await page.goto("/");
  await expect(taigaCardLink).toBeVisible({ timeout: 60_000 });
  await taigaCardLink.click();

  await expect(taigaIframe).toBeVisible({ timeout: 60_000 });
  const taigaFrame = taigaIframe.contentFrame();

  if (taigaOauth2Enabled) {
    await waitForFrameUrl(
      taigaIframe,
      taigaUrls.expectedOidcAuthUrl,
      60_000,
      `Expected Taiga iframe to navigate to Keycloak auth via oauth2-proxy: ${taigaUrls.expectedOidcAuthUrl}`
    );
  } else {
    const initialAuthState = await waitForInitialTaigaAuthState(
      page,
      taigaIframe,
      taigaFrame,
      taigaUrls.expectedTaigaBaseUrl,
      taigaUrls.expectedOidcAuthUrl,
      60_000,
      "Expected Taiga iframe to expose either the Taiga OIDC entry point or the Keycloak login page"
    );

    if (initialAuthState.kind === "taiga-oidc-entry") {
      await initialAuthState.locator.click();
      await waitForFrameUrl(
        taigaIframe,
        taigaUrls.expectedOidcAuthUrl,
        60_000,
        `Expected Taiga OIDC login to navigate to Keycloak auth: ${taigaUrls.expectedOidcAuthUrl}`
      );
    }
  }

  const usernameField = taigaFrame.locator("input[name='username'], input#username");
  const passwordField = taigaFrame.locator("input[name='password'], input#password");
  const signInButton = taigaFrame.locator(
    "input#kc-login, button#kc-login, button[type='submit'], input[type='submit']"
  );

  await expect(usernameField.first()).toBeVisible({ timeout: 60_000 });
  await usernameField.first().fill(loginUsername);
  await passwordField.first().fill(loginPassword);
  await signInButton.first().click();

  await waitForFrameUrl(
    taigaIframe,
    taigaUrls.expectedTaigaBaseUrl,
    60_000,
    `Expected Taiga iframe to redirect back to Taiga after Keycloak login: ${taigaUrls.expectedTaigaBaseUrl}`
  );

  if (taigaOauth2Enabled) {
    await waitForOauth2ProxyCookie(
      page,
      taigaUrls.expectedTaigaBaseUrl,
      true,
      60_000,
      "Expected Taiga to establish an oauth2-proxy session after the Keycloak login redirect"
    );
  }

  await waitForAuthenticatedTaigaShell(
    taigaFrame,
    60_000,
    "Timed out waiting for a signed-in Taiga shell after the Keycloak login redirect"
  );

  return {
    ...taigaUrls,
    taigaFrame,
    taigaIframe
  };
}

async function logoutFromTaigaAndDashboard(page, session) {
  if (taigaOauth2Enabled) {
    await page.goto(session.taigaOauth2SignOutUrl);
    await waitForOauth2ProxyCookie(
      page,
      session.expectedTaigaBaseUrl,
      false,
      60_000,
      "Expected Taiga oauth2-proxy session cookie to be cleared after /oauth2/sign_out"
    );
  } else {
    await page.goto(session.expectedTaigaBaseUrl);
    await waitForAuthenticatedTaigaShell(
      page,
      60_000,
      "Timed out waiting for the top-level signed-in Taiga shell before logout"
    );
    await tryLogoutFromTaiga(page, page);
  }

  await page.goto("/");
  await logoutFromDashboardIfNeeded(page);
  await page.goto(session.expectedTaigaBaseUrl);

  const loggedOutState = await waitForTopLevelLoginRequirement(
    page,
    session.expectedTaigaBaseUrl,
    session.expectedOidcAuthUrl,
    60_000,
    "Expected logged-out access to Taiga to require a fresh login"
  );

  if (taigaOauth2Enabled) {
    expect(loggedOutState.kind).toBe("keycloak");
    await expect(page.locator("input[name='username'], input#username").first()).toBeVisible({ timeout: 60_000 });
    await expect
      .poll(
        async () => page.url(),
        {
          timeout: 60_000,
          message: "Expected top-level Taiga re-entry to stay on the Keycloak login page after logout"
        }
      )
      .toContain(session.expectedOidcAuthUrl);
    return;
  }

  expect(["keycloak", "taiga-login-page", "taiga-oidc-entry"]).toContain(loggedOutState.kind);

  if (loggedOutState.kind === "keycloak") {
    await expect(page.locator("input[name='username'], input#username").first()).toBeVisible({ timeout: 60_000 });
    return;
  }

  await expect(loggedOutState.locator).toBeVisible({ timeout: 60_000 });
}

async function reachTopLevelTaigaAuthEntry(page, taigaUrls, timeout, errorMessage) {
  const deadline = Date.now() + timeout;
  let loginClicked = false;

  while (Date.now() < deadline) {
    const currentUrl = page.url();
    const keycloakUsernameField = page.locator("input[name='username'], input#username");

    if (
      currentUrl.includes(taigaUrls.expectedOidcAuthUrl) &&
      (await keycloakUsernameField.first().isVisible().catch(() => false))
    ) {
      return { kind: "keycloak" };
    }

    if (currentUrl.includes(taigaUrls.expectedTaigaBaseUrl)) {
      const oidcEntry = await findFirstVisible(getOidcEntryLocators(page));

      if (oidcEntry) {
        return { kind: "taiga-oidc-entry", locator: oidcEntry };
      }

      const loginEntry = await findFirstVisible([
        page.getByRole("link", { name: /^Login$/i }),
        page.getByRole("button", { name: /^Login$/i })
      ]);

      if (loginEntry && !loginClicked) {
        await loginEntry.click();
        loginClicked = true;
        await page.waitForTimeout(500);
        continue;
      }

      const visibleLocalLoginField = await findFirstVisible([
        page.locator("input[name='username'], input#username"),
        page.locator("input[name='password'], input#password")
      ]);

      if (visibleLocalLoginField) {
        await page.waitForTimeout(1_000);

        const persistedLocalLoginField = await findFirstVisible([
          page.locator("input[name='username'], input#username"),
          page.locator("input[name='password'], input#password")
        ]);

        if (persistedLocalLoginField) {
          return { kind: "taiga-local-login-visible", locator: persistedLocalLoginField };
        }
      }
    }

    await page.waitForTimeout(500);
  }

  throw new Error(errorMessage);
}

test.beforeEach(() => {
  expect(taigaBaseUrl, "TAIGA_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(loginUsername, "LOGIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(loginPassword, "LOGIN_PASSWORD must be set in the Playwright env file").toBeTruthy();

  if (taigaOauth2Enabled || taigaOidcEnabled) {
    expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set in the Playwright env file").toBeTruthy();
  }
});

test("dashboard to taiga login and logout", async ({ page }) => {
  test.skip(
    !taigaOauth2Enabled && !taigaOidcEnabled,
    "Taiga auth flow requires oauth2 or oidc to be enabled."
  );

  const session = await loginToTaigaFromDashboard(page);
  await logoutFromTaigaAndDashboard(page, session);
});

test("taiga public discover keeps the themed surface and hides local login fields when oidc is active", async ({ page }) => {
  test.skip(!taigaOidcEnabled, "This scenario only applies when the Taiga OIDC integration is enabled.");

  const taigaUrls = getTaigaUrls();

  await page.goto(taigaUrls.discoverUrl);
  await expect(page.getByRole("heading", { name: /discover projects/i })).toBeVisible({ timeout: 60_000 });
  await expectGradientBackground(
    page.locator("div.master"),
    "Expected the Taiga discover page to use the themed master background"
  );
  await expectGradientBackground(
    page.locator(".discover-header form"),
    "Expected the Taiga discover search form to use the themed surface"
  );
  await expectGradientBackground(
    page.locator(".discover-header input[type='text']"),
    "Expected the Taiga discover search input to use the themed input surface"
  );

  const authState = await reachTopLevelTaigaAuthEntry(
    page,
    taigaUrls,
    60_000,
    "Expected Taiga to expose either the OIDC entry point or the Keycloak login page"
  );

  expect(authState.kind).not.toBe("taiga-local-login-visible");

  if (authState.kind === "taiga-oidc-entry") {
    await expect(authState.locator).toBeVisible({ timeout: 60_000 });
    await expect
      .poll(
        async () => page.locator("input[name='username'], input#username").first().isVisible().catch(() => false),
        {
          timeout: 10_000,
          message: "Expected the local Taiga username field to stay hidden when OIDC is active"
        }
      )
      .toBe(false);
    await expect
      .poll(
        async () => page.locator("input[name='password'], input#password").first().isVisible().catch(() => false),
        {
          timeout: 10_000,
          message: "Expected the local Taiga password field to stay hidden when OIDC is active"
        }
      )
      .toBe(false);
    await expect
      .poll(
        async () => page.getByText(/^or login with$/i).first().isVisible().catch(() => false),
        {
          timeout: 10_000,
          message: "Expected the legacy Taiga OIDC helper text to stay hidden when OIDC is active"
        }
      )
      .toBe(false);
    await expect
      .poll(
        async () => page.getByText(/^forgot it\?$/i).first().isVisible().catch(() => false),
        {
          timeout: 10_000,
          message: "Expected the legacy Taiga password reset helper text to stay hidden when OIDC is active"
        }
      )
      .toBe(false);

    await authState.locator.click();
    await expect
      .poll(
        async () => page.url(),
        {
          timeout: 60_000,
          message: `Expected the Taiga OIDC entry to navigate to Keycloak: ${taigaUrls.expectedOidcAuthUrl}`
        }
      )
      .toContain(taigaUrls.expectedOidcAuthUrl);
  }

  await expect(page.locator("input[name='username'], input#username").first()).toBeVisible({ timeout: 60_000 });
});

test("taiga themed routes stay aligned across stable routes", async ({ page }) => {
  const session = await loginToTaigaFromDashboard(page);

  const routeChecks = [
    {
      url: session.discoverUrl,
      ready: page.getByRole("heading", { name: /discover projects/i }),
      surface: page.locator(".discover-header form"),
      field: page.locator(".discover-header input[type='text']")
    },
    {
      url: session.projectsUrl,
      ready: page.getByRole("heading", { name: /my projects/i }),
      surface: page.locator(".project-list-wrapper")
    },
    {
      url: session.userSettingsUrl,
      ready: page.getByRole("heading", { name: /user settings/i }),
      surface: page.locator(".menu-secondary")
    }
  ];

  for (const routeCheck of routeChecks) {
    await page.goto(routeCheck.url);
    await expect(routeCheck.ready).toBeVisible({ timeout: 60_000 });

    await expectGradientBackground(
      page.locator("div.master"),
      `Expected the Taiga master background to stay themed on ${routeCheck.url}`
    );

    if (routeCheck.surface) {
      await expectGradientBackground(
        routeCheck.surface,
        `Expected the primary Taiga surface to stay themed on ${routeCheck.url}`
      );
    }

    if (routeCheck.field) {
      await expectGradientBackground(
        routeCheck.field,
        `Expected the Taiga input surface to stay themed on ${routeCheck.url}`
      );
    }

    if (routeCheck.action) {
      await expectGradientBackground(
        routeCheck.action,
        `Expected the main Taiga action button to stay themed on ${routeCheck.url}`
      );
    }
  }

  await logoutFromTaigaAndDashboard(page, session);
});
