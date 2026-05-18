// Shared dashboard Playwright spec state: env vars, the `beforeEach`
// env-presence guard, and helpers reused across multiple scenarios
// (diagnostics collection, dashboard-ready wait, network-response
// poller). `playwright.spec.js` wires the lifecycle hook and `require()`s
// one test module per scenario so each test stays atomar and individually
// inspectable.

const { expect } = require("@playwright/test");

const {
  assertCspMetaParity,
  assertCspResponseHeader,
  decodeDotenvQuotedValue,
  expectNoCspViolations,
  installCspViolationObserver,
  normalizeBaseUrl,
  runAdminFlow,
  runBiberFlow,
  runGuestFlow,
} = require("./personas");
const { skipUnlessServiceEnabled } = require("./service-gating");

const appBaseUrl = normalizeBaseUrl(process.env.APP_BASE_URL || "");
const oidcIssuerUrl = normalizeBaseUrl(process.env.OIDC_ISSUER_URL || "");
const loginUsername = decodeDotenvQuotedValue(process.env.LOGIN_USERNAME);
const loginPassword = decodeDotenvQuotedValue(process.env.LOGIN_PASSWORD);
const cdnBaseUrl = normalizeBaseUrl(process.env.CDN_BASE_URL || "");
const dashboardJsBaseUrl = normalizeBaseUrl(process.env.DASHBOARD_JS_BASE_URL || "");
const matomoBaseUrl = normalizeBaseUrl(process.env.MATOMO_BASE_URL || "");
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN);
const platformLogoUrl = decodeDotenvQuotedValue(process.env.PLATFORM_LOGO_URL);
const platformFaviconUrl = decodeDotenvQuotedValue(process.env.PLATFORM_FAVICON_URL);
const companyLogoUrl = decodeDotenvQuotedValue(process.env.COMPANY_LOGO_URL);

function buildAssetPathPrefix(baseUrl, path) {
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

const sharedCssPrefix = buildAssetPathPrefix(cdnBaseUrl, "/_shared/css");
const sharedJsPrefix = buildAssetPathPrefix(cdnBaseUrl, "/_shared/js");
const roleCssPrefix = buildAssetPathPrefix(cdnBaseUrl, "/roles/web-app-dashboard/latest/css");
const expectedOidcAuthUrl = `${oidcIssuerUrl}/protocol/openid-connect/auth`;

const dashboardTargetRoles = (() => {
  const raw = process.env.DASHBOARD_TARGET_ROLES_JSON || "[]";
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
})();

async function beforeEach({ page }) {
  await page.setViewportSize({ width: 1440, height: 1100 });

  expect(appBaseUrl, "APP_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set in the Playwright env file").toBeTruthy();
  expect(loginUsername, "LOGIN_USERNAME must be set in the Playwright env file").toBeTruthy();
  expect(loginPassword, "LOGIN_PASSWORD must be set in the Playwright env file").toBeTruthy();
  expect(cdnBaseUrl, "CDN_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(dashboardJsBaseUrl, "DASHBOARD_JS_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(matomoBaseUrl, "MATOMO_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set in the Playwright env file").toBeTruthy();
  expect(platformLogoUrl, "PLATFORM_LOGO_URL must be set in the Playwright env file").toBeTruthy();
  expect(platformFaviconUrl, "PLATFORM_FAVICON_URL must be set in the Playwright env file").toBeTruthy();
  expect(companyLogoUrl, "COMPANY_LOGO_URL must be set in the Playwright env file").toBeTruthy();

  await page.context().clearCookies();
  await installCspViolationObserver(page);
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
        columnNumber: location.columnNumber,
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
      resourceType: response.request().resourceType(),
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

async function waitForResourceResponse(records, partialUrl, label) {
  await expect
    .poll(
      () =>
        records.some((record) => record.url.includes(partialUrl) && record.status >= 200 && record.status < 400),
      {
        timeout: 60_000,
        message: `Expected ${label} to load successfully (${partialUrl})`,
      }
    )
    .toBe(true);
}

module.exports = {
  env: {
    appBaseUrl,
    oidcIssuerUrl,
    loginUsername,
    loginPassword,
    cdnBaseUrl,
    dashboardJsBaseUrl,
    matomoBaseUrl,
    canonicalDomain,
    platformLogoUrl,
    platformFaviconUrl,
    companyLogoUrl,
    sharedCssPrefix,
    sharedJsPrefix,
    roleCssPrefix,
    expectedOidcAuthUrl,
    dashboardTargetRoles,
  },
  skipUnlessServiceEnabled,
  beforeEach,
  attachDiagnostics,
  expectNoUnexpectedDiagnostics,
  waitForDashboardReady,
  waitForResourceResponse,
  runAdminFlow,
  runBiberFlow,
  runGuestFlow,
  assertCspMetaParity,
  assertCspResponseHeader,
  expectNoCspViolations,
};
