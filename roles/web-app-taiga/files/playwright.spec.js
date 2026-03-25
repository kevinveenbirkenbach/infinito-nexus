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
const taigaBaseUrl = decodeDotenvQuotedValue(process.env.TAIGA_BASE_URL);

async function isVisible(locator) {
  return locator.first().isVisible().catch(() => false);
}

async function getOauth2ProxyCookies(page, baseUrl) {
  const cookies = await page.context().cookies(baseUrl);
  return cookies.filter((cookie) => /oauth2/i.test(cookie.name));
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

test.beforeEach(() => {
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set in the Playwright env file").toBeTruthy();
  expect(taigaBaseUrl, "TAIGA_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(loginUsername, "LOGIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(loginPassword, "LOGIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
});

test("dashboard to taiga login and logout", async ({ page }) => {
  const expectedOidcAuthUrl = `${oidcIssuerUrl.replace(/\/$/, "")}/protocol/openid-connect/auth`;
  const expectedTaigaBaseUrl = taigaBaseUrl.replace(/\/$/, "");
  const taigaOauth2SignOutUrl = `${expectedTaigaBaseUrl}/oauth2/sign_out`;
  const taigaCardLink = page.getByRole("link", { name: "Explore Taiga" });
  const taigaIframe = page.locator("#main iframe");

  await page.goto("/");
  await taigaCardLink.click();

  await expect(taigaIframe).toBeVisible();
  await waitForFrameUrl(
    taigaIframe,
    expectedOidcAuthUrl,
    60_000,
    `Expected Taiga iframe to navigate to Keycloak OIDC auth endpoint: ${expectedOidcAuthUrl}`
  );

  const taigaFrame = taigaIframe.contentFrame();
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

  await waitForOauth2ProxyCookie(
    page,
    expectedTaigaBaseUrl,
    true,
    60_000,
    "Expected Taiga to establish an oauth2-proxy session after the Keycloak login redirect"
  );
  await waitForAuthenticatedTaigaShell(
    taigaFrame,
    60_000,
    "Timed out waiting for a signed-in Taiga shell after the Keycloak login redirect"
  );

  await page.goto(taigaOauth2SignOutUrl);
  await waitForOauth2ProxyCookie(
    page,
    expectedTaigaBaseUrl,
    false,
    60_000,
    "Expected Taiga oauth2-proxy session cookie to be cleared after /oauth2/sign_out"
  );

  await page.goto("/");

  const accountItem = page.locator("nav").getByText("Account", { exact: true });
  const loginItem = page.locator("nav").getByText("Login", { exact: true });
  const logoutItem = page.locator("nav").getByText("Logout", { exact: true });

  await expect
    .poll(
      async () => (await isVisible(accountItem)) || (await isVisible(loginItem)),
      {
        timeout: 60_000,
        message: "Expected dashboard to expose either the authenticated Account menu or the Login entry after Taiga sign-out"
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

  await page.goto(expectedTaigaBaseUrl);
  await expect
    .poll(
      async () => page.url(),
      {
        timeout: 60_000,
        message: "Expected logged-out access to Taiga to require a fresh Keycloak login"
      }
    )
    .toContain(
      expectedOidcAuthUrl
    );

  const topLevelUsernameField = page.locator("input[name='username'], input#username");
  await expect(topLevelUsernameField.first()).toBeVisible({ timeout: 60_000 });
  await expect
    .poll(
      async () => page.url(),
      {
        timeout: 60_000,
        message: "Expected top-level Taiga re-entry to stay on the Keycloak login page after logout"
      }
    )
    .toContain(
      expectedOidcAuthUrl
    );
});
