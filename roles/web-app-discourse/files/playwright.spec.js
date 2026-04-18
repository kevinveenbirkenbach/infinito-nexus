const { test, expect } = require("@playwright/test");

test.use({ ignoreHTTPSErrors: true });

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

async function performOidcLogin(frame, username, password) {
  const usernameField = frame.locator("input[name='username'], input#username").first();
  const passwordField = frame.locator("input[name='password'], input#password").first();
  const signInButton = frame
    .locator("input#kc-login, button#kc-login, button[type='submit'], input[type='submit']")
    .first();

  await expect(usernameField).toBeVisible({ timeout: 60_000 });
  await usernameField.fill(username);
  await usernameField.press("Tab");
  await passwordField.fill(password);
  await signInButton.click();
}

async function discourseLogout(page, discourseBaseUrl) {
  await page
    .goto(`${discourseBaseUrl}/session/destroy`, { waitUntil: "commit" })
    .catch(() => {});
  await page
    .goto(`${oidcIssuerUrl}/protocol/openid-connect/logout`, { waitUntil: "commit" })
    .catch(() => {});
  await page.context().clearCookies();
}

const dashboardBaseUrl = normalizeBaseUrl(process.env.APP_BASE_URL || "");
const oidcIssuerUrl = normalizeBaseUrl(process.env.OIDC_ISSUER_URL || "");
const discourseBaseUrl = normalizeBaseUrl(process.env.DISCOURSE_BASE_URL || "");
const adminUsername = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const biberUsername = decodeDotenvQuotedValue(process.env.BIBER_USERNAME);
const biberPassword = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD);
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN);

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });

  expect(dashboardBaseUrl, "APP_BASE_URL must be set (dashboard entry)").toBeTruthy();
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set").toBeTruthy();
  expect(discourseBaseUrl, "DISCOURSE_BASE_URL must be set").toBeTruthy();
  expect(adminUsername, "ADMIN_USERNAME must be set").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set").toBeTruthy();
  expect(biberUsername, "BIBER_USERNAME must be set").toBeTruthy();
  expect(biberPassword, "BIBER_PASSWORD must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();

  await page.context().clearCookies();
  await installCspViolationObserver(page);
});

test("discourse enforces Content-Security-Policy and exposes canonical domain from applications lookup", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);

  const response = await page.goto(`${discourseBaseUrl}/`);
  expect(response, "Expected discourse landing response").toBeTruthy();
  expect(response.status(), "Expected discourse landing response to be successful").toBeLessThan(400);

  const directives = assertCspResponseHeader(response, "discourse landing");
  await assertCspMetaParity(page, directives, "discourse landing");

  const documentUrl = response.url();
  expect(
    documentUrl.includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" (from applications lookup) to back the discourse URL`
  ).toBe(true);

  await expectNoCspViolations(page, diagnostics, "discourse landing");
});

async function signInViaDashboardOidc(page, username, password, personaLabel) {
  const expectedOidcAuthUrl = `${oidcIssuerUrl}/protocol/openid-connect/auth`;

  await page.goto(`${dashboardBaseUrl}/`);
  await expect(page.locator("body"), `${personaLabel}: expected dashboard body to load`).toBeVisible({ timeout: 60_000 });

  await page.goto(`${discourseBaseUrl}/`);

  const oidcSignIn = page
    .locator("a, button")
    .filter({ hasText: /sign\s*in\s+with\s+oidc|sign\s*in\s+with\s+sso|continue\s+with\s+oidc|continue\s+with\s+sso|single\s+sign[-\s]*on|log\s*in|sign\s*up/i })
    .first();

  if ((await oidcSignIn.count().catch(() => 0)) > 0) {
    await oidcSignIn.click();
  } else {
    await page.goto(`${discourseBaseUrl}/auth/oidc`).catch(() => {});
  }

  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `${personaLabel}: expected redirect to Keycloak OIDC auth (${expectedOidcAuthUrl})`
    })
    .toContain(expectedOidcAuthUrl);

  await performOidcLogin(page, username, password);

  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `${personaLabel}: expected redirect back to discourse at ${discourseBaseUrl}`
    })
    .toContain(discourseBaseUrl);
}

test("administrator: dashboard to discourse OIDC login and logout", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);

  await signInViaDashboardOidc(page, adminUsername, adminPassword, "administrator");

  await expect(page.locator("body")).toContainText(/topic|category|welcome|latest|discourse/i, { timeout: 60_000 });

  await discourseLogout(page, discourseBaseUrl);

  await page.goto(`${discourseBaseUrl}/`);
  await expect
    .poll(
      async () =>
        (await page
          .locator("a, button")
          .filter({ hasText: /sign\s*up|log\s*in|anmelden|continue\s+with/i })
          .first()
          .count()
          .catch(() => 0)) > 0,
      {
        timeout: 60_000,
        message: "Expected discourse to require a new sign-in after logout"
      }
    )
    .toBe(true);

  await expectNoCspViolations(page, diagnostics, "discourse administrator OIDC");
});

test("biber: dashboard to discourse OIDC login and logout", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);

  await signInViaDashboardOidc(page, biberUsername, biberPassword, "biber");

  await expect(page.locator("body")).toContainText(/topic|category|welcome|latest|discourse/i, { timeout: 60_000 });

  await discourseLogout(page, discourseBaseUrl);

  await page.goto(`${discourseBaseUrl}/`);
  await expect
    .poll(
      async () =>
        (await page
          .locator("a, button")
          .filter({ hasText: /sign\s*up|log\s*in|anmelden|continue\s+with/i })
          .first()
          .count()
          .catch(() => 0)) > 0,
      {
        timeout: 60_000,
        message: "Expected discourse to require a new sign-in after logout"
      }
    )
    .toBe(true);

  await expectNoCspViolations(page, diagnostics, "discourse biber OIDC");
});
