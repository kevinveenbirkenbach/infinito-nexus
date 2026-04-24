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

const appBaseUrl = normalizeBaseUrl(process.env.APP_BASE_URL || "");
const adminUsername = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN);

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });

  expect(appBaseUrl, "APP_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(adminUsername, "ADMIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set in the Playwright env file").toBeTruthy();

  await page.context().clearCookies();
  await installCspViolationObserver(page);
});

test("matomo enforces Content-Security-Policy and exposes canonical domain from applications lookup", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);

  const response = await page.goto(`${appBaseUrl}/`);
  expect(response, "Expected Matomo login response").toBeTruthy();
  expect(response.status(), "Expected Matomo login response to be successful").toBeLessThan(400);

  const directives = assertCspResponseHeader(response, "matomo login");
  await assertCspMetaParity(page, directives, "matomo login");

  const documentHtml = await response.text();
  const documentUrl = response.url();
  expect(
    documentHtml.includes(canonicalDomain) || documentUrl.includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" (from applications lookup) to appear in the Matomo login document`
  ).toBe(true);

  await expectNoCspViolations(page, diagnostics, "matomo login");
});

test("matomo local administrator logs in and logs out", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);

  await page.goto(`${appBaseUrl}/index.php?module=Login`);

  const usernameField = page
    .locator("input#login_form_login, input[name='form_login']")
    .first();
  const passwordField = page
    .locator("input#login_form_password, input[name='form_password']")
    .first();
  const submitButton = page
    .locator("input#login_form_submit, button#login_form_submit, button[type='submit'], input[type='submit']")
    .first();

  await expect(usernameField, "Expected Matomo login form username field").toBeVisible({ timeout: 60_000 });
  await usernameField.fill(adminUsername);
  await passwordField.fill(adminPassword);
  await submitButton.click();

  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: "Expected Matomo login to leave the Login module"
    })
    .not.toContain("module=Login");

  await expect(page.locator("body")).toContainText(/dashboard|websites|matomo/i, { timeout: 60_000 });

  await page.goto(`${appBaseUrl}/index.php?module=Login&action=logout`);

  await expect
    .poll(
      async () =>
        (await page
          .locator("input#login_form_login, input[name='form_login']")
          .first()
          .count()
          .catch(() => 0)) > 0,
      {
        timeout: 60_000,
        message: "Expected Matomo login form to reappear after logout"
      }
    )
    .toBe(true);

  await expectNoCspViolations(page, diagnostics, "matomo administrator login");
});
