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
      consoleErrors.push(message.text());
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

  const loaded = await locator.evaluate((img) => {
    return Boolean((img.currentSrc || img.src || "").includes("/static/cache/")) && img.naturalWidth > 0;
  });

  expect(loaded, `${label} should resolve to a cached local image asset`).toBe(true);
}

async function getHeaderNavigation(page) {
  const headerNav = page.locator("nav.menu-header").first();
  await expect(headerNav).toBeVisible({ timeout: 60_000 });
  return headerNav;
}

async function isDropdownMenuOpen(trigger, menu) {
  const expanded = await trigger.getAttribute("aria-expanded").catch(() => null);
  const menuOpen = await menu
    .evaluate((element) => {
      const style = window.getComputedStyle(element);
      return (
        element.classList.contains("show") ||
        (style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0")
      );
    })
    .catch(() => false);

  return expanded === "true" || menuOpen;
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
    async () => trigger.press("Enter"),
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

async function clickAccountLogout(page) {
  const headerNav = await getHeaderNavigation(page);
  const accountDropdown = headerNav.locator(".nav-item.dropdown").filter({ hasText: "Account" }).first();
  const accountTrigger = accountDropdown.locator(".dropdown-toggle").first();
  const accountMenu = accountDropdown.locator(".dropdown-menu").first();
  const logoutItem = accountMenu.getByRole("link", { name: "Logout" }).first();

  await expect(accountTrigger).toBeVisible({ timeout: 60_000 });
  await openDropdownMenu(accountTrigger, accountMenu, "Account");
  await expect(logoutItem).toBeVisible({ timeout: 10_000 });
  await logoutItem.click();
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

test("dashboard loads injected css, matomo, logout, javascript, simpleicons, and logo assets", async ({ page }) => {
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
  await waitForResourceResponse(diagnostics.responses, `${matomoBaseUrl}/matomo.js`, "Matomo tracking script");

  expect(documentHtml).toContain(sharedCssPrefix);
  expect(documentHtml).toContain(`${sharedCssPrefix}/default.css`);
  expect(documentHtml).toContain(`${sharedCssPrefix}/bootstrap.css`);
  expect(documentHtml).toContain(`${roleCssPrefix}/style.css`);
  expect(documentHtml).toContain(`${sharedJsPrefix}/logout.js`);
  expect(documentHtml).toContain("loadScriptSequential");
  expect(documentHtml).toContain(dashboardJsBaseUrl);
  expect(documentHtml).toContain('"iframe.js"');
  expect(documentHtml).toContain('"oidc.js"');
  expect(documentHtml).toContain("matomo.js");
  expect(documentHtml).toContain("matomo.php?idsite=");
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

  const iframeTargetUrl = `${matomoBaseUrl}/index.php`;

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

  expect(diagnostics.pageErrors, `Unexpected page errors: ${diagnostics.pageErrors.join("\n")}`).toEqual([]);
  expect(diagnostics.consoleErrors, `Unexpected console errors: ${diagnostics.consoleErrors.join("\n")}`).toEqual([]);
});

test("dashboard login and logout returns to a clearly logged-out state", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);

  await page.goto("/");
  await waitForDashboardReady(page);
  await waitForResourceResponse(diagnostics.responses, `${dashboardJsBaseUrl}/oidc.js`, "dashboard oidc script");

  const headerNav = await getHeaderNavigation(page);
  const loginEntry = headerNav.getByText("Login", { exact: true }).first();
  const accountEntry = headerNav.getByText("Account", { exact: true }).first();

  await expect
    .poll(
      async () => (await isVisible(loginEntry)) && !(await isVisible(accountEntry)),
      {
        timeout: 60_000,
        message: "Expected dashboard OIDC JavaScript to expose Login and hide Account before authentication"
      }
    )
    .toBe(true);

  await loginEntry.click();

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
  await expect
    .poll(
      async () => (await isVisible(accountEntry)) && !(await isVisible(loginEntry)),
      {
        timeout: 60_000,
        message: "Expected dashboard OIDC JavaScript to expose Account and hide Login after authentication"
      }
    )
    .toBe(true);

  await clickAccountLogout(page);

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

  await expect
    .poll(
      async () => (await isVisible(loginEntry)) && !(await isVisible(accountEntry)),
      {
        timeout: 60_000,
        message: "Expected dashboard to return to the logged-out state after logout"
      }
    )
    .toBe(true);

  expect(diagnostics.pageErrors, `Unexpected page errors: ${diagnostics.pageErrors.join("\n")}`).toEqual([]);
  expect(diagnostics.consoleErrors, `Unexpected console errors: ${diagnostics.consoleErrors.join("\n")}`).toEqual([]);
});
