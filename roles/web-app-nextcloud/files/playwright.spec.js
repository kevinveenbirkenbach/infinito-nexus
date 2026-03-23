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
const loginUsername = decodeDotenvQuotedValue(process.env.LOGIN_USERNAME);
const loginPassword = decodeDotenvQuotedValue(process.env.LOGIN_PASSWORD);
const oidcIssuerUrl = decodeDotenvQuotedValue(process.env.OIDC_ISSUER_URL);
const nextcloudBaseUrl = decodeDotenvQuotedValue(process.env.NEXTCLOUD_BASE_URL);

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

  throw new Error("Timed out waiting for one of the expected Nextcloud selectors to become visible");
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
  errorMessage = "Timed out waiting for one of the expected Nextcloud selectors to become visible"
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

test.beforeEach(() => {
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set in the Playwright env file").toBeTruthy();
  expect(nextcloudBaseUrl, "NEXTCLOUD_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(loginUsername, "LOGIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(loginPassword, "LOGIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
});

test("dashboard to nextcloud login", async ({ page }) => {
  const expectedOidcAuthUrl = `${oidcIssuerUrl.replace(/\/$/, "")}/protocol/openid-connect/auth`;
  const expectedNextcloudBaseUrl = nextcloudBaseUrl.replace(/\/$/, "");

  await page.goto("/");
  await page.getByRole("link", { name: "Explore Nextcloud" }).click();

  const nextcloudIframe = page.locator("#main iframe");
  const nextcloudFrame = nextcloudIframe.contentFrame();
  const usernameField = nextcloudFrame.getByRole("textbox", { name: "Username or email" });
  const passwordField = nextcloudFrame.getByRole("textbox", { name: "Password" });
  const rememberMeCheckbox = nextcloudFrame.getByRole("checkbox", { name: "Remember me" });
  const signInButton = nextcloudFrame.getByRole("button", { name: "Sign In" });
  const settingsMenuButton = nextcloudFrame.getByRole("button", { name: "Settings menu" });
  const userMenuTriggerByControls = nextcloudFrame.locator('[aria-controls="header-menu-user-menu"]');
  const userMenuTriggerInMount = nextcloudFrame.locator("#user-menu button");
  const nextcloudAppShell = nextcloudFrame.locator(
    "#app-content-vue, #app-navigation-vue, #app-content, #content-vue, #appmenu"
  );
  const nextcloudPrimaryNavigation = nextcloudFrame.locator(
    'a[href*="/apps/files"], a[href*="/apps/dashboard"]'
  );
  const logoutLinkByName = nextcloudFrame.getByRole("link", { name: "Log out" });
  const logoutLinkById = nextcloudFrame.locator("#logout");
  const logoutLinkByHref = nextcloudFrame.locator('a[href*="logout"]');
  const logoutConfirmButton = nextcloudFrame.getByRole("button", { name: "Logout" });
  const userMenuCandidates = [
    { kind: "user-menu", locator: userMenuTriggerByControls },
    { kind: "user-menu", locator: settingsMenuButton },
    { kind: "user-menu", locator: userMenuTriggerInMount }
  ];
  const postLoginCandidates = [
    ...userMenuCandidates,
    { kind: "shell", locator: nextcloudAppShell },
    { kind: "shell", locator: nextcloudPrimaryNavigation }
  ];

  await expect(nextcloudIframe).toBeVisible();
  await expect
    .poll(
      async () => {
        const iframeHandle = await nextcloudIframe.elementHandle();
        const iframeFrame = iframeHandle ? await iframeHandle.contentFrame() : null;

        return iframeFrame ? iframeFrame.url() : "";
      },
      {
        timeout: 60_000,
        message: `Expected Nextcloud iframe to navigate to Keycloak OIDC auth endpoint: ${expectedOidcAuthUrl}`
      }
    )
    .toContain(expectedOidcAuthUrl);

  await waitForFirstVisible(page, [usernameField, signInButton], 60_000);

  await expect(usernameField).toBeVisible();
  await usernameField.click();
  await usernameField.fill(loginUsername);
  await usernameField.press("Tab");
  await passwordField.fill(loginPassword);

  if (await rememberMeCheckbox.first().isVisible().catch(() => false)) {
    await rememberMeCheckbox.check();
  } else {
    await nextcloudFrame.getByText("Remember me").click({ timeout: 2_000 }).catch(() => {});
  }

  await signInButton.click();
  await expect
    .poll(
      async () => {
        const iframeHandle = await nextcloudIframe.elementHandle();
        const iframeFrame = iframeHandle ? await iframeHandle.contentFrame() : null;

        return iframeFrame ? iframeFrame.url() : "";
      },
      {
        timeout: 60_000,
        message: `Expected Nextcloud iframe to redirect back to Nextcloud after Keycloak login: ${expectedNextcloudBaseUrl}`
      }
    )
    .toContain(expectedNextcloudBaseUrl);

  const postLoginState = await waitForVisibleCandidate(
    page,
    postLoginCandidates,
    60_000,
    "Timed out waiting for a signed-in Nextcloud shell after the Keycloak login redirect"
  );

  await expect(postLoginState.locator).toBeVisible();

  // Embedded Nextcloud layouts can hide the user menu even when the login succeeded.
  const userMenuState = postLoginState.kind === "user-menu"
    ? postLoginState
    : await waitForVisibleCandidate(page, userMenuCandidates, 10_000).catch(() => null);

  if (!userMenuState) {
    await page.goto("/");
    return;
  }

  await userMenuState.locator.click();

  const logoutLink = await waitForFirstVisible(
    page,
    [logoutLinkByName, logoutLinkById, logoutLinkByHref],
    15_000
  );

  await expect(logoutLink).toBeVisible();
  await logoutLink.click();

  const logoutConfirmationVisible = await logoutConfirmButton
    .first()
    .waitFor({ state: "visible", timeout: 10_000 })
    .then(() => true)
    .catch(() => false);

  if (logoutConfirmationVisible) {
    await logoutConfirmButton.click();
  }

  await page.goto("/");
});
