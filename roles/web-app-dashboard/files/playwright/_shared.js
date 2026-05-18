// Shared dashboard Playwright spec state — only carries values and
// helpers used by ≥ 2 ``test-*.js`` modules. Single-consumer constants,
// helpers, and persona-flow re-exports live in the test file that
// needs them; their existence here would be a "shared" lie that masks
// the real consumer relationship.

const { expect } = require("@playwright/test");

const { normalizeBaseUrl } = require("./personas");
const { skipUnlessServiceEnabled } = require("./service-gating");

const dashboardJsBaseUrl = normalizeBaseUrl(process.env.DASHBOARD_JS_BASE_URL || "");
const matomoBaseUrl = normalizeBaseUrl(process.env.MATOMO_BASE_URL || "");

async function beforeEach({ page }) {
  await page.setViewportSize({ width: 1440, height: 1100 });

  expect(dashboardJsBaseUrl, "DASHBOARD_JS_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(matomoBaseUrl, "MATOMO_BASE_URL must be set in the Playwright env file").toBeTruthy();

  await page.context().clearCookies();
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

// Keycloak JS adapter loads a hidden silent-check-sso.html iframe to
// refresh the session in the background. In test envs the dashboard
// origin is not whitelisted as a Keycloak frame-ancestor (CSP), so the
// iframe load is blocked and chrome surfaces a console.error from
// chrome-error://chromewebdata/. That is environment noise, not a
// dashboard regression.
function isOidcSilentCheckNoise(record) {
  if (!record) {
    return false;
  }
  const text = typeof record === "string" ? record : record.text || "";
  const url = typeof record === "string" ? "" : record.url || "";
  return (
    url.startsWith("chrome-error://chromewebdata") ||
    /^Framing '/.test(text) ||
    /silent-check-sso/i.test(text) ||
    /silent-check-sso/i.test(url)
  );
}

function expectNoUnexpectedDiagnostics(
  diagnostics,
  { ignoreMatomoConsoleNoise = false, ignoreOidcSilentCheckNoise = false } = {}
) {
  expect(diagnostics.pageErrors, `Unexpected page errors: ${diagnostics.pageErrors.join("\n")}`).toEqual([]);
  let unexpectedConsoleErrors = diagnostics.consoleErrors;
  if (ignoreMatomoConsoleNoise) {
    unexpectedConsoleErrors = unexpectedConsoleErrors.filter((record) => !isMatomoConsoleNoise(record));
  }
  if (ignoreOidcSilentCheckNoise) {
    unexpectedConsoleErrors = unexpectedConsoleErrors.filter((record) => !isOidcSilentCheckNoise(record));
  }
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
    dashboardJsBaseUrl,
    matomoBaseUrl,
  },
  skipUnlessServiceEnabled,
  beforeEach,
  attachDiagnostics,
  expectNoUnexpectedDiagnostics,
  waitForDashboardReady,
  waitForResourceResponse,
};
