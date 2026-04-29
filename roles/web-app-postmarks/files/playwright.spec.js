const { test, expect } = require("@playwright/test");

test.use({ ignoreHTTPSErrors: true });

function decodeDotenvQuotedValue(value) {
  if (typeof value !== "string" || value.length < 2) return value;
  if (!(value.startsWith('"') && value.endsWith('"'))) return value;
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

const baseUrl = normalizeBaseUrl(process.env.POSTMARKS_BASE_URL || "");
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN || "");

test.beforeEach(async ({ page }) => {
  expect(baseUrl, "POSTMARKS_BASE_URL must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  await page.context().clearCookies();
});

test("postmarks responds under canonical domain", async ({ page }) => {
  // Postmarks has no in-app authorisation tier beyond "logged in or
  // not". When SSO is required, it is provided by a sidecar
  // oauth2-proxy in front of the Postmarks web UI; the RBAC
  // exception is documented in README.md per requirement 013.
  const response = await page.goto(`${baseUrl}/`);
  expect(response, "Expected postmarks response").toBeTruthy();
  expect(response.status(), "Expected postmarks status < 500").toBeLessThan(500);
  expect(
    response.url().includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" to back the postmarks URL`
  ).toBe(true);
});
