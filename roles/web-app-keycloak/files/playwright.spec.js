const { test, expect } = require("@playwright/test");

test.use({ ignoreHTTPSErrors: true });

// -----------------------------------------------------------------------------
// Shared helpers (inlined on purpose: the runner only stages this file).
// -----------------------------------------------------------------------------

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

function attachDiagnostics(page) {
  const consoleErrors = [];
  const pageErrors = [];
  const cspRelated = [];

  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }

    if (/content security policy|csp/i.test(message.text())) {
      cspRelated.push({ source: "console", text: message.text() });
    }
  });

  page.on("pageerror", (error) => {
    const text = String(error);
    pageErrors.push(text);

    if (/content security policy|csp/i.test(text)) {
      cspRelated.push({ source: "pageerror", text });
    }
  });

  return { consoleErrors, pageErrors, cspRelated };
}

function installCspViolationObserver(page) {
  return page.addInitScript(() => {
    window.__cspViolations = [];
    window.addEventListener("securitypolicyviolation", (event) => {
      window.__cspViolations.push({
        violatedDirective: event.violatedDirective,
        blockedURI: event.blockedURI,
        sourceFile: event.sourceFile,
        lineNumber: event.lineNumber,
        originalPolicy: event.originalPolicy
      });
    });
  });
}

async function readCspViolations(page) {
  return page.evaluate(() => window.__cspViolations || []).catch(() => []);
}

const EXPECTED_CSP_DIRECTIVES = [
  "default-src",
  "connect-src",
  "frame-ancestors",
  "frame-src",
  "script-src",
  "script-src-elem",
  "script-src-attr",
  "style-src",
  "style-src-elem",
  "style-src-attr",
  "font-src",
  "worker-src",
  "manifest-src",
  "media-src",
  "img-src"
];

function parseCspHeader(value) {
  const result = {};

  if (!value) {
    return result;
  }

  for (const raw of value.split(";")) {
    const trimmed = raw.trim();
    if (!trimmed) continue;

    const parts = trimmed.split(/\s+/);
    const directive = parts.shift();
    if (!directive) continue;

    result[directive.toLowerCase()] = parts;
  }

  return result;
}

function assertCspResponseHeader(response, label) {
  const headers = response.headers();
  const cspHeader = headers["content-security-policy"];

  expect(cspHeader, `${label}: Content-Security-Policy response header MUST be present`).toBeTruthy();

  const reportOnly = headers["content-security-policy-report-only"];
  expect(
    reportOnly,
    `${label}: Content-Security-Policy-Report-Only MUST NOT be set (policy must be enforced)`
  ).toBeFalsy();

  const parsed = parseCspHeader(cspHeader);
  const missing = EXPECTED_CSP_DIRECTIVES.filter((directive) => !parsed[directive]);

  expect(
    missing,
    `${label}: CSP directives missing from response header: ${missing.join(", ")}`
  ).toEqual([]);

  return parsed;
}

async function assertCspMetaParity(page, headerDirectives, label) {
  const metaLocator = page.locator('meta[http-equiv="Content-Security-Policy"]').first();
  const hasMeta = (await metaLocator.count().catch(() => 0)) > 0;

  if (!hasMeta) {
    return;
  }

  const metaContent = await metaLocator.getAttribute("content").catch(() => null);

  if (!metaContent) {
    return;
  }

  const metaParsed = parseCspHeader(metaContent);

  for (const directive of Object.keys(metaParsed)) {
    const headerTokens = new Set(headerDirectives[directive] || []);
    const metaTokens = metaParsed[directive] || [];

    for (const token of metaTokens) {
      expect(
        headerTokens.has(token),
        `${label}: CSP meta token "${token}" for directive ${directive} MUST also appear in the response header`
      ).toBe(true);
    }
  }
}

async function expectNoCspViolations(page, diagnostics, label) {
  const domViolations = await readCspViolations(page);

  expect(
    domViolations,
    `${label}: securitypolicyviolation events observed: ${JSON.stringify(domViolations)}`
  ).toEqual([]);

  expect(
    diagnostics.cspRelated,
    `${label}: CSP-related console/pageerror entries observed: ${JSON.stringify(diagnostics.cspRelated)}`
  ).toEqual([]);
}

async function fillKeycloakLoginForm(page, username, password) {
  const usernameField = page.locator("input[name='username'], input#username").first();
  const passwordField = page.locator("input[name='password'], input#password").first();
  const signInButton = page
    .locator("input#kc-login, button#kc-login, button[type='submit'], input[type='submit']")
    .first();

  await expect(usernameField, "Expected Keycloak username field to be visible").toBeVisible({ timeout: 60_000 });
  await usernameField.fill(username);
  await passwordField.fill(password);
  await signInButton.click();
}

async function keycloakSignOutFromAccountConsole(page) {
  const signOutButton = page
    .locator("button, a")
    .filter({ hasText: /sign\s*out|logout|abmelden/i })
    .first();

  if ((await signOutButton.count().catch(() => 0)) === 0) {
    return;
  }

  await signOutButton.click().catch(() => {});
  await page.waitForLoadState("networkidle").catch(() => {});
}

async function keycloakSignOutFromMasterAdminConsole(page, appBaseUrl) {
  await page
    .goto(`${appBaseUrl}/realms/master/protocol/openid-connect/logout`, { waitUntil: "commit" })
    .catch(() => {});
  await page.context().clearCookies().catch(() => {});
}

// -----------------------------------------------------------------------------
// Test configuration
// -----------------------------------------------------------------------------

const appBaseUrl = normalizeBaseUrl(process.env.APP_BASE_URL || "");
const realmName = decodeDotenvQuotedValue(process.env.KEYCLOAK_REALM_NAME);
const superAdminUsername = decodeDotenvQuotedValue(process.env.SUPER_ADMIN_USERNAME);
const superAdminPassword = decodeDotenvQuotedValue(process.env.SUPER_ADMIN_PASSWORD);
const adminUsername = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const biberUsername = decodeDotenvQuotedValue(process.env.BIBER_USERNAME);
const biberPassword = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD);
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN);

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });

  expect(appBaseUrl, "APP_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(realmName, "KEYCLOAK_REALM_NAME must be set in the Playwright env file").toBeTruthy();
  expect(superAdminUsername, "SUPER_ADMIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(superAdminPassword, "SUPER_ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(adminUsername, "ADMIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(biberUsername, "BIBER_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(biberPassword, "BIBER_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set in the Playwright env file").toBeTruthy();

  await page.context().clearCookies();
  await installCspViolationObserver(page);
});

test("keycloak enforces Content-Security-Policy and exposes canonical domain from applications lookup", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);

  const response = await page.goto(`${appBaseUrl}/realms/${realmName}/account/`);
  expect(response, "Expected Keycloak account page response").toBeTruthy();
  expect(response.status(), "Expected Keycloak account page to respond successfully").toBeLessThan(400);

  const directives = assertCspResponseHeader(response, "keycloak account page");
  await assertCspMetaParity(page, directives, "keycloak account page");

  const documentHtml = await response.text();
  expect(
    documentHtml.includes(canonicalDomain) || (await page.content()).includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" (from applications lookup) to appear in the Keycloak UI`
  ).toBe(true);

  await expectNoCspViolations(page, diagnostics, "keycloak account page");
});

test("master-realm super administrator logs into Keycloak admin console and logs out", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);

  const response = await page.goto(`${appBaseUrl}/admin/master/console/`);
  expect(response, "Expected Keycloak admin console response").toBeTruthy();
  expect(response.status(), "Expected Keycloak admin console response to be successful").toBeLessThan(400);

  assertCspResponseHeader(response, "keycloak admin console");

  await fillKeycloakLoginForm(page, superAdminUsername, superAdminPassword);

  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: "Expected super admin login to leave the Keycloak login page"
    })
    .not.toContain("/login-actions/authenticate");

  await expect(page.locator("body")).toContainText(/master|realm|clients|users/i, { timeout: 60_000 });

  await keycloakSignOutFromMasterAdminConsole(page, appBaseUrl);

  await page.goto(`${appBaseUrl}/admin/master/console/`);
  await expect(
    page.locator("input[name='username'], input#username").first(),
    "Expected Keycloak admin console to require login again after sign out"
  ).toBeVisible({ timeout: 60_000 });

  await expectNoCspViolations(page, diagnostics, "keycloak admin console");
});

test("normal-realm administrator logs in through account interface and logs out", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);

  const accountUrl = `${appBaseUrl}/realms/${realmName}/account/`;
  const response = await page.goto(accountUrl);
  expect(response, "Expected normal-realm account page response").toBeTruthy();
  expect(response.status(), "Expected normal-realm account page response to be successful").toBeLessThan(400);

  assertCspResponseHeader(response, "keycloak normal-realm account (administrator)");

  const signInButton = page.locator("a, button").filter({ hasText: /sign\s*in|log\s*in|anmelden/i }).first();

  if ((await signInButton.count().catch(() => 0)) > 0) {
    await signInButton.click();
  }

  await fillKeycloakLoginForm(page, adminUsername, adminPassword);

  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: "Expected administrator login to reach the account interface"
    })
    .toContain("/account");

  await expect(page.locator("body")).toContainText(new RegExp(adminUsername, "i"), { timeout: 60_000 });

  await keycloakSignOutFromAccountConsole(page);

  await page.goto(accountUrl);
  const postLogoutSignIn = page.locator("a, button").filter({ hasText: /sign\s*in|log\s*in|anmelden/i }).first();
  const usernameField = page.locator("input[name='username'], input#username").first();

  await expect
    .poll(
      async () =>
        (await postLogoutSignIn.count().catch(() => 0)) > 0 || (await usernameField.count().catch(() => 0)) > 0,
      {
        timeout: 60_000,
        message: "Expected account interface to require login again after administrator sign out"
      }
    )
    .toBe(true);

  await expectNoCspViolations(page, diagnostics, "keycloak normal-realm account (administrator)");
});

test("normal-realm biber logs in through account interface and logs out", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);

  const accountUrl = `${appBaseUrl}/realms/${realmName}/account/`;
  const response = await page.goto(accountUrl);
  expect(response, "Expected normal-realm account page response").toBeTruthy();
  expect(response.status(), "Expected normal-realm account page response to be successful").toBeLessThan(400);

  assertCspResponseHeader(response, "keycloak normal-realm account (biber)");

  const signInButton = page.locator("a, button").filter({ hasText: /sign\s*in|log\s*in|anmelden/i }).first();

  if ((await signInButton.count().catch(() => 0)) > 0) {
    await signInButton.click();
  }

  await fillKeycloakLoginForm(page, biberUsername, biberPassword);

  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: "Expected biber login to reach the account interface"
    })
    .toContain("/account");

  await expect(page.locator("body")).toContainText(/personal\s*info|account|profile|signing\s*in/i, { timeout: 60_000 });

  await keycloakSignOutFromAccountConsole(page);

  await page.goto(accountUrl);
  const postLogoutSignIn = page.locator("a, button").filter({ hasText: /sign\s*in|log\s*in|anmelden/i }).first();
  const usernameField = page.locator("input[name='username'], input#username").first();

  await expect
    .poll(
      async () =>
        (await postLogoutSignIn.count().catch(() => 0)) > 0 || (await usernameField.count().catch(() => 0)) > 0,
      {
        timeout: 60_000,
        message: "Expected account interface to require login again after biber sign out"
      }
    )
    .toBe(true);

  await expectNoCspViolations(page, diagnostics, "keycloak normal-realm account (biber)");
});
