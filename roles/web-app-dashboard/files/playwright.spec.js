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

function normalizeBaseUrl(value) {
  return decodeDotenvQuotedValue(value || "").replace(/\/$/, "");
}

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function buildAssetPathPrefix(baseUrl, path) {
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

async function isVisible(locator) {
  return locator.first().isVisible().catch(() => false);
}

async function waitForFirstVisible(locators, timeout, errorMessage) {
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    for (const locator of locators) {
      const candidate = locator.first();

      if (await candidate.isVisible().catch(() => false)) {
        return candidate;
      }
    }

    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  throw new Error(errorMessage);
}

function attachDiagnostics(page) {
  const consoleErrors = [];
  const pageErrors = [];
  const responses = [];

  page.on("console", (message) => {
    if (message.type() === "error") {
      const location = message.location();

      consoleErrors.push({
        text: message.text(),
        url: location.url || "",
        lineNumber: location.lineNumber,
        columnNumber: location.columnNumber
      });
    }
  });

  page.on("pageerror", (error) => {
    pageErrors.push(String(error));
  });

  page.on("response", (response) => {
    responses.push({
      url: response.url(),
      status: response.status(),
      resourceType: response.request().resourceType()
    });
  });

  return { consoleErrors, pageErrors, responses };
}

function formatConsoleError(record) {
  if (!record || typeof record === "string") {
    return String(record || "");
  }

  if (!record.url) {
    return record.text;
  }

  return `${record.text} (${record.url}:${record.lineNumber}:${record.columnNumber})`;
}

function formatConsoleErrors(records) {
  return records.map((record) => formatConsoleError(record)).join("\n");
}

function isMatomoConsoleNoise(record) {
  if (!record) {
    return false;
  }

  const text = typeof record === "string" ? record : record.text || "";
  const url = typeof record === "string" ? "" : record.url || "";

  return (
    url.startsWith(matomoBaseUrl) ||
    /matomo/i.test(text) ||
    /_pk_(id|ses)\./i.test(text) ||
    /There was an error setting cookie/i.test(text) ||
    /Can't write cookie on domain/i.test(text)
  );
}

function expectNoUnexpectedDiagnostics(diagnostics, { ignoreMatomoConsoleNoise = false } = {}) {
  expect(diagnostics.pageErrors, `Unexpected page errors: ${diagnostics.pageErrors.join("\n")}`).toEqual([]);

  const unexpectedConsoleErrors = ignoreMatomoConsoleNoise
    ? diagnostics.consoleErrors.filter((record) => !isMatomoConsoleNoise(record))
    : diagnostics.consoleErrors;

  expect(
    unexpectedConsoleErrors,
    `Unexpected console errors: ${formatConsoleErrors(unexpectedConsoleErrors)}`
  ).toEqual([]);
}

async function waitForDashboardReady(page) {
  await expect(page.locator("main#main")).toBeVisible({ timeout: 60_000 });
  await expect(page.locator("header.header")).toBeVisible({ timeout: 60_000 });
  await expect(page.locator("#navbar_logo img")).toBeVisible({ timeout: 60_000 });
}

async function getComputedStyleProperty(locator, propertyName) {
  return locator.evaluate(
    (element, requestedProperty) => window.getComputedStyle(element).getPropertyValue(requestedProperty),
    propertyName
  );
}

async function expectDashboardCssEffects(page) {
  const styledCardIcon = page.locator(".card-img-top i").first();

  if ((await styledCardIcon.count().catch(() => 0)) > 0) {
    const iconFilter = await getComputedStyleProperty(styledCardIcon, "filter");
    expect(iconFilter, "Expected dashboard card icons to receive the role-local drop shadow style").not.toBe("none");
    return;
  }

  const navbarToggler = page.locator(".navbar-toggler").first();

  if ((await navbarToggler.count().catch(() => 0)) > 0) {
    const backgroundColor = await getComputedStyleProperty(navbarToggler, "background-color");
    expect(
      backgroundColor,
      "Expected the dashboard navbar toggler to receive the role-local background color override"
    ).not.toBe("rgba(0, 0, 0, 0)");
    return;
  }

  throw new Error("Expected a dashboard element that demonstrates the role-local CSS to be present");
}

async function expectStableCardHover(page, cardTitle) {
  const card = page
    .locator(".card")
    .filter({
      has: page.locator(".card-title", {
        hasText: new RegExp(`^${escapeRegex(cardTitle)}$`)
      })
    })
    .first();

  await expect(card, `Expected the ${cardTitle} card to be visible`).toBeVisible({ timeout: 60_000 });

  const stretchedLink = card.locator("a.btn.stretched-link").first();
  await expect(stretchedLink, `Expected the ${cardTitle} card to expose a stretched-link button`).toBeVisible({
    timeout: 60_000
  });

  const cardBox = await card.boundingBox();
  expect(cardBox, `Expected the ${cardTitle} card to expose a measurable bounding box`).toBeTruthy();

  const hoverPoints = [
    { x: 0.5, y: 0.2 },
    { x: 0.5, y: 0.5 },
    { x: 0.5, y: 0.8 }
  ];

  for (const point of hoverPoints) {
    const x = Math.round(cardBox.x + cardBox.width * point.x);
    const y = Math.round(cardBox.y + cardBox.height * point.y);

    await page.mouse.move(x, y);
    await expect
      .poll(
        () => stretchedLink.evaluate((element) => element.matches(":hover")),
        {
          timeout: 2_000,
          message: `Expected the ${cardTitle} stretched-link overlay to stay hovered across the card`
        }
      )
      .toBe(true);
  }

  await stretchedLink.hover();
  const hoverFilter = await getComputedStyleProperty(stretchedLink, "filter");
  expect(hoverFilter.trim() || "none", `Expected the ${cardTitle} stretched-link hover filter to stay disabled`).toBe(
    "none"
  );
}

async function waitForResourceResponse(records, partialUrl, label) {
  await expect
    .poll(
      () =>
        records.some((record) => record.url.includes(partialUrl) && record.status >= 200 && record.status < 400),
      {
        timeout: 60_000,
        message: `Expected ${label} to load successfully (${partialUrl})`
      }
    )
    .toBe(true);
}

async function getCurrentImageSource(locator) {
  return locator.evaluate((img) => img.currentSrc || img.src || "");
}

async function expectImageLoaded(locator, label) {
  await expect(locator).toBeVisible({ timeout: 60_000 });

  const loaded = await locator.evaluate((img) => ({
    source: img.currentSrc || img.src || "",
    naturalWidth: img.naturalWidth
  }));

  expect(loaded.source, `${label} should resolve to a cached local dashboard image asset`).toContain("/static/cache/");
  expect(loaded.naturalWidth, `${label} should resolve to a non-empty dashboard image asset`).toBeGreaterThan(0);
}

async function getHeaderNavigation(page) {
  const headerNav = page.locator("nav.menu-header").first();
  await expect(headerNav).toBeVisible({ timeout: 60_000 });
  return headerNav;
}

async function getHeaderAuthControls(page) {
  const headerNav = await getHeaderNavigation(page);
  const loginTrigger = headerNav.locator("a, button").filter({ hasText: /login/i }).first();
  const accountTrigger = headerNav.getByRole("button", { name: /account/i }).first();
  const accountMenu = headerNav.locator(".dropdown-menu").filter({ hasText: /logout/i }).first();

  return { loginTrigger, accountTrigger, accountMenu };
}

async function expectLoggedOutHeaderAuthState(page) {
  const controls = await getHeaderAuthControls(page);

  await expect
    .poll(
      async () => await isVisible(controls.loginTrigger),
      {
        timeout: 60_000,
        message: "Expected dashboard OIDC JavaScript to expose Login before authentication"
      }
    )
    .toBe(true);

  await expect
    .poll(
      async () => await isVisible(controls.accountTrigger),
      {
        timeout: 60_000,
        message: "Expected dashboard OIDC JavaScript to keep Account hidden before authentication"
      }
    )
    .toBe(false);

  return controls;
}

async function expectLoggedInHeaderAuthState(page) {
  const controls = await getHeaderAuthControls(page);

  await expect
    .poll(
      async () => await isVisible(controls.accountTrigger),
      {
        timeout: 60_000,
        message: "Expected dashboard OIDC JavaScript to automatically switch the header button to Account"
      }
    )
    .toBe(true);

  await expect(controls.accountTrigger).toContainText(/Account/, { timeout: 60_000 });

  await expect
    .poll(
      async () => await isVisible(controls.loginTrigger),
      {
        timeout: 60_000,
        message: "Expected dashboard OIDC JavaScript to hide Login after authentication"
      }
    )
    .toBe(false);

  return controls;
}

async function isDropdownMenuOpen(trigger, menu) {
  const expanded = await trigger.getAttribute("aria-expanded").catch(() => null);
  const menuRoot = menu.first();
  const menuHasShowClass = await menuRoot.evaluate((element) => element.classList.contains("show")).catch(() => false);
  const menuVisible = await menuRoot.isVisible().catch(() => false);
  const interactiveItemVisible = await menuRoot
    .locator("a, button, [role='menuitem'], [role='link']")
    .first()
    .isVisible()
    .catch(() => false);

  return expanded === "true" || (menuVisible && (menuHasShowClass || interactiveItemVisible));
}

async function waitForDropdownMenuOpen(trigger, menu, label, timeout = 3_000) {
  await expect
    .poll(
      async () => isDropdownMenuOpen(trigger, menu),
      {
        timeout,
        message: `Expected the ${label} dropdown menu to open`
      }
    )
    .toBe(true);
}

async function openDropdownMenu(trigger, menu, label) {
  if (await isDropdownMenuOpen(trigger, menu)) {
    return;
  }

  const openAttempts = [
    async () => trigger.click(),
    async () => trigger.hover(),
    async () => trigger.press("Enter"),
    async () => trigger.press(" "),
    async () => trigger.click({ force: true }),
    async () =>
      trigger.evaluate((element) => {
        element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
      })
  ];

  for (const attempt of openAttempts) {
    await attempt().catch(() => {});

    try {
      await waitForDropdownMenuOpen(trigger, menu, label, 2_500);
      return;
    } catch {
      // Try the next interaction strategy.
    }
  }

  throw new Error(`Unable to open the ${label} dropdown menu`);
}

async function findAccountLogoutItem(accountMenu) {
  return waitForFirstVisible(
    [
      accountMenu.getByRole("link", { name: /logout/i }),
      accountMenu.locator("a[href*='logout'], a[href*='signout'], a[href*='sign-out']"),
      accountMenu.locator("a, button, [role='link']").filter({ hasText: /logout/i })
    ],
    10_000,
    "Timed out waiting for the Account logout entry"
  );
}

async function confirmLogoutIfNeeded(page) {
  const logoutConfirmCandidates = [
    page.getByRole("button", { name: /logout|sign out|continue/i }),
    page.locator("button[type='submit'], input[type='submit'], #kc-logout, #kc-logout-confirm")
  ];

  const logoutConfirmButton = await waitForFirstVisible(
    logoutConfirmCandidates,
    5_000,
    "Timed out waiting for an optional Keycloak logout confirmation button"
  ).catch(() => null);

  if (logoutConfirmButton) {
    await logoutConfirmButton.click().catch(() => {});
  }
}

const appBaseUrl = normalizeBaseUrl(process.env.APP_BASE_URL || "");
const oidcIssuerUrl = normalizeBaseUrl(process.env.OIDC_ISSUER_URL || "");
const loginUsername = decodeDotenvQuotedValue(process.env.LOGIN_USERNAME);
const loginPassword = decodeDotenvQuotedValue(process.env.LOGIN_PASSWORD);
const cdnBaseUrl = normalizeBaseUrl(process.env.CDN_BASE_URL || "");
const dashboardJsBaseUrl = normalizeBaseUrl(process.env.DASHBOARD_JS_BASE_URL || "");
const matomoBaseUrl = normalizeBaseUrl(process.env.MATOMO_BASE_URL || "");

const sharedCssPrefix = buildAssetPathPrefix(cdnBaseUrl, "/_shared/css");
const sharedJsPrefix = buildAssetPathPrefix(cdnBaseUrl, "/_shared/js");
const roleCssPrefix = buildAssetPathPrefix(cdnBaseUrl, "/roles/web-app-dashboard/latest/css");
const expectedOidcAuthUrl = `${oidcIssuerUrl}/protocol/openid-connect/auth`;

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });

  expect(appBaseUrl, "APP_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set in the Playwright env file").toBeTruthy();
  expect(loginUsername, "LOGIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(loginPassword, "LOGIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(cdnBaseUrl, "CDN_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(dashboardJsBaseUrl, "DASHBOARD_JS_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(matomoBaseUrl, "MATOMO_BASE_URL must be set in the Playwright env file").toBeTruthy();

  await page.context().clearCookies();
});

test("dashboard loads core css, javascript, simpleicons, and logo assets", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);
  const documentResponse = await page.goto("/");

  expect(documentResponse, "Expected the dashboard document response to exist").toBeTruthy();
  expect(documentResponse.status(), "Expected the dashboard document response to be successful").toBeLessThan(400);

  const documentHtml = await documentResponse.text();

  await waitForDashboardReady(page);
  await waitForResourceResponse(diagnostics.responses, "/_shared/css/default.css", "shared default CSS");
  await waitForResourceResponse(diagnostics.responses, "/_shared/css/bootstrap.css", "shared bootstrap CSS");
  await waitForResourceResponse(diagnostics.responses, "/roles/web-app-dashboard/latest/css/style.css", "dashboard role CSS");
  await waitForResourceResponse(diagnostics.responses, "/_shared/js/logout.js", "logout injector script");
  await waitForResourceResponse(diagnostics.responses, `${dashboardJsBaseUrl}/iframe.js`, "dashboard iframe sync script");
  await waitForResourceResponse(diagnostics.responses, `${dashboardJsBaseUrl}/oidc.js`, "dashboard oidc script");

  expect(documentHtml).toContain(sharedCssPrefix);
  expect(documentHtml).toContain(`${sharedCssPrefix}/default.css`);
  expect(documentHtml).toContain(`${sharedCssPrefix}/bootstrap.css`);
  expect(documentHtml).toContain(`${roleCssPrefix}/style.css`);
  expect(documentHtml).toContain(`${sharedJsPrefix}/logout.js`);
  expect(documentHtml).toContain("loadScriptSequential");
  expect(documentHtml).toContain(dashboardJsBaseUrl);
  expect(documentHtml).toContain('"iframe.js"');
  expect(documentHtml).toContain('"oidc.js"');
  await expectDashboardCssEffects(page);

  const headerLogo = page.locator("header.header img[alt='logo']").first();
  const navbarLogo = page.locator("#navbar_logo img").first();

  await expectImageLoaded(headerLogo, "Header logo");
  await expectImageLoaded(navbarLogo, "Navbar logo");

  const headerLogoSrc = await getCurrentImageSource(headerLogo);
  const navbarLogoSrc = await getCurrentImageSource(navbarLogo);

  expect(headerLogoSrc).toBe(navbarLogoSrc);

  const simpleiconCard = page
    .locator(".card")
    .filter({
      has: page.locator(".card-img-top svg, .card-img-top img[src*='/static/cache/']")
    })
    .first();

  await expect(
    simpleiconCard,
    "Expected at least one dashboard card to render a Simple Icons-backed SVG or cached image asset"
  ).toBeVisible({ timeout: 60_000 });
  await expect(
    simpleiconCard.locator(".card-img-top svg, .card-img-top img[src*='/static/cache/']").first()
  ).toBeVisible({ timeout: 60_000 });
  await expectStableCardHover(page, "Keycloak");

  const iframeTargetUrl = `${matomoBaseUrl}/?playwright-iframe-sync=1`;

  await page.evaluate(({ href, origin }) => {
    const event = new MessageEvent("message", {
      origin,
      data: {
        type: "iframeLocationChange",
        href
      }
    });

    window.dispatchEvent(event);
  }, {
    href: iframeTargetUrl,
    origin: new URL(iframeTargetUrl).origin
  });

  await expect
    .poll(() => {
      return page.evaluate(() => new URL(window.location.href).searchParams.get("iframe"));
    }, {
      timeout: 10_000,
      message: "Expected dashboard iframe sync JavaScript to update the iframe query parameter"
    })
    .toBe(iframeTargetUrl);

  expectNoUnexpectedDiagnostics(diagnostics, { ignoreMatomoConsoleNoise: true });
});

test("dashboard integrates matomo tracking assets", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);
  const documentResponse = await page.goto("/");

  expect(documentResponse, "Expected the dashboard document response to exist").toBeTruthy();
  expect(documentResponse.status(), "Expected the dashboard document response to be successful").toBeLessThan(400);

  const documentHtml = await documentResponse.text();

  await waitForDashboardReady(page);
  await waitForResourceResponse(diagnostics.responses, `${matomoBaseUrl}/matomo.js`, "Matomo tracking script");

  expect(documentHtml).toContain("matomo.js");
  expect(documentHtml).toContain("matomo.php?idsite=");

  expectNoUnexpectedDiagnostics(diagnostics);
});

test("dashboard login automatically switches Login to Account and exposes Logout under Account", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);

  await page.goto("/");
  await waitForDashboardReady(page);
  await waitForResourceResponse(diagnostics.responses, `${dashboardJsBaseUrl}/oidc.js`, "dashboard oidc script");

  const loggedOutControls = await expectLoggedOutHeaderAuthState(page);
  await loggedOutControls.loginTrigger.click();

  const usernameField = page.locator("input[name='username'], input#username").first();
  const passwordField = page.locator("input[name='password'], input#password").first();
  const signInButton = page.locator("input#kc-login, button#kc-login, button[type='submit'], input[type='submit']").first();

  await expect
    .poll(
      async () => page.url().includes(expectedOidcAuthUrl) || (await isVisible(usernameField)),
      {
        timeout: 60_000,
        message: `Expected the dashboard login flow to reach the Keycloak auth page: ${expectedOidcAuthUrl}`
      }
    )
    .toBe(true);

  await expect(usernameField).toBeVisible({ timeout: 60_000 });
  await usernameField.fill(loginUsername);
  await passwordField.fill(loginPassword);
  await signInButton.click();

  await expect
    .poll(
      async () => page.url().startsWith(appBaseUrl),
      {
        timeout: 60_000,
        message: `Expected Keycloak login to redirect back to the dashboard: ${appBaseUrl}`
      }
    )
    .toBe(true);

  await waitForDashboardReady(page);
  const loggedInControls = await expectLoggedInHeaderAuthState(page);
  await openDropdownMenu(loggedInControls.accountTrigger, loggedInControls.accountMenu, "Account");

  const logoutEntry = await findAccountLogoutItem(loggedInControls.accountMenu);
  await expect(logoutEntry).toBeVisible({ timeout: 10_000 });
  await expect(logoutEntry).toContainText(/logout/i);
  await logoutEntry.click();

  await expect
    .poll(
      async () => page.url().includes("/protocol/openid-connect/logout") || page.url().startsWith(appBaseUrl),
      {
        timeout: 30_000,
        message: "Expected dashboard logout to reach Keycloak logout or redirect back to the dashboard"
      }
    )
    .toBe(true);

  if (page.url().includes("/protocol/openid-connect/logout")) {
    await confirmLogoutIfNeeded(page);
  }

  await page.goto("/");
  await waitForDashboardReady(page);
  await expectLoggedOutHeaderAuthState(page);

  expectNoUnexpectedDiagnostics(diagnostics, { ignoreMatomoConsoleNoise: true });
});
