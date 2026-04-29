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

const baseUrl = normalizeBaseUrl(process.env.LIBRETRANSLATE_BASE_URL || "");
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN || "");

test.beforeEach(async ({ page }) => {
  expect(baseUrl, "LIBRETRANSLATE_BASE_URL must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  await page.context().clearCookies();
});

test("libretranslate UI is served under canonical domain", async ({ page }) => {
  // LibreTranslate authenticates programmatic clients with API keys
  // and decouples its in-app authorisation from any IdP. The OIDC
  // path is via a sidecar oauth2-proxy on the UI subpath only;
  // LDAP and RBAC are documented exceptions in README.md per
  // requirement 013.
  const response = await page.goto(`${baseUrl}/`);
  expect(response, "Expected libretranslate response").toBeTruthy();
  expect(response.status(), "Expected libretranslate status < 500").toBeLessThan(500);
  expect(
    response.url().includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" to back the libretranslate URL`
  ).toBe(true);
});

test("libretranslate /languages API responds", async ({ request }) => {
  // The /languages endpoint is anonymous in the upstream default
  // image and returns the list of supported language pairs. It is
  // the simplest "the API is alive" probe and MUST stay reachable
  // even when the UI is OIDC-gated, per the LibreTranslate per-role
  // notes in requirement 013.
  const response = await request.get(`${baseUrl}/languages`);
  expect(response.status(), "Expected libretranslate /languages status < 500").toBeLessThan(500);
});
