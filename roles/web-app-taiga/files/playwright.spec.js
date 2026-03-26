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
  const accountItem = page.locator("nav").getByText("Account", { exact: true });
  const loginItem = page.locator("nav").getByText("Login", { exact: true });
  const logoutItem = page.locator("nav").getByText("Logout", { exact: true });

  await expect
    .poll(
      async () => (await isVisible(accountItem)) || (await isVisible(loginItem)),
      {
        timeout: 60_000,
        message: "Expected dashboard to expose either the authenticated Account menu or the Login entry after the Taiga flow"
      }
    )
    .toBe(true);

  if (await isVisible(accountItem)) {
    await accountItem.first().click();
    await expect(logoutItem.first()).toBeVisible({ timeout: 10_000 });
    await logoutItem.first().click();
  }

  await expect
    .poll(
      async () => (await isVisible(loginItem)) && !(await isVisible(accountItem)),
      {
        timeout: 60_000,
        message: "Expected dashboard to show the Login entry again after logout"
      }
    )
    .toBe(true);
}

async function tryLogoutFromTaiga(page, taigaFrame) {
  const directLogoutLocators = [
    taigaFrame.getByRole("link", { name: /log ?out/i }),
    taigaFrame.getByRole("button", { name: /log ?out/i }),
    taigaFrame.locator('[href*="logout"], [ui-sref*="logout"], [ng-click*="logout"]')
  ];
  const menuTriggerLocators = [
    taigaFrame.locator("[aria-haspopup='true']"),
    taigaFrame.locator(".user-avatar, .avatar, .profile-avatar, .profile-button, [class*='avatar']"),
    taigaFrame.getByText(loginUsername, { exact: false })
  ];

  const directLogout = await findFirstVisible(directLogoutLocators);
  if (directLogout) {
    await directLogout.click({ timeout: 2_000 }).catch(() => {});
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
      return true;
    }
  }

  return false;
}

async function waitForAuthenticatedTaigaShell(frame, timeout, errorMessage) {
  await expect
    .poll(
      async () => {
        const bodyText = await frame.locator("body").innerText().catch(() => "");
        const loginFormVisible = await frame
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
      const oidcEntry = await findFirstVisible(getOidcEntryLocators(page));

      if (oidcEntry) {
        return { kind: "taiga-oidc-entry", locator: oidcEntry };
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

  const expectedOidcAuthUrl = `${oidcIssuerUrl.replace(/\/$/, "")}/protocol/openid-connect/auth`;
  const expectedTaigaBaseUrl = taigaBaseUrl.replace(/\/$/, "");
  const taigaOauth2SignOutUrl = `${expectedTaigaBaseUrl}/oauth2/sign_out`;
  const taigaCardLink = page.getByRole("link", { name: "Explore Taiga" });
  const taigaIframe = page.locator("#main iframe");

  await page.goto("/");
  await taigaCardLink.click();

  await expect(taigaIframe).toBeVisible();
  const taigaFrame = taigaIframe.contentFrame();

  if (taigaOauth2Enabled) {
    await waitForFrameUrl(
      taigaIframe,
      expectedOidcAuthUrl,
      60_000,
      `Expected Taiga iframe to navigate to Keycloak auth via oauth2-proxy: ${expectedOidcAuthUrl}`
    );
  } else {
    const initialAuthState = await waitForInitialTaigaAuthState(
      page,
      taigaIframe,
      taigaFrame,
      expectedTaigaBaseUrl,
      expectedOidcAuthUrl,
      60_000,
      "Expected Taiga iframe to expose either the Taiga OIDC entry point or the Keycloak login page"
    );

    if (initialAuthState.kind === "taiga-oidc-entry") {
      await initialAuthState.locator.click();
      await waitForFrameUrl(
        taigaIframe,
        expectedOidcAuthUrl,
        60_000,
        `Expected Taiga OIDC login to navigate to Keycloak auth: ${expectedOidcAuthUrl}`
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
    expectedTaigaBaseUrl,
    60_000,
    `Expected Taiga iframe to redirect back to Taiga after Keycloak login: ${expectedTaigaBaseUrl}`
  );

  if (taigaOauth2Enabled) {
    await waitForOauth2ProxyCookie(
      page,
      expectedTaigaBaseUrl,
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

  if (taigaOauth2Enabled) {
    await page.goto(taigaOauth2SignOutUrl);
    await waitForOauth2ProxyCookie(
      page,
      expectedTaigaBaseUrl,
      false,
      60_000,
      "Expected Taiga oauth2-proxy session cookie to be cleared after /oauth2/sign_out"
    );
  } else {
    await tryLogoutFromTaiga(page, taigaFrame);
  }

  await page.goto("/");
  await logoutFromDashboardIfNeeded(page);

  await page.goto(expectedTaigaBaseUrl);

  const loggedOutState = await waitForTopLevelLoginRequirement(
    page,
    expectedTaigaBaseUrl,
    expectedOidcAuthUrl,
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
      .toContain(expectedOidcAuthUrl);
  } else {
    expect(["keycloak", "taiga-oidc-entry"]).toContain(loggedOutState.kind);

    if (loggedOutState.kind === "keycloak") {
      await expect(page.locator("input[name='username'], input#username").first()).toBeVisible({ timeout: 60_000 });
    } else {
      await expect(loggedOutState.locator).toBeVisible({ timeout: 60_000 });
    }
  }
});
