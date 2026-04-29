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

const baseUrl = normalizeBaseUrl(process.env.BLUESKY_BASE_URL || "");
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN || "");

test.beforeEach(async ({ page }) => {
  expect(baseUrl, "BLUESKY_BASE_URL must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  await page.context().clearCookies();
});

test("bluesky web app responds under canonical domain", async ({ page }) => {
  // The Bluesky social-app web client is the user-visible surface;
  // its OIDC and LDAP auth paths require the Keycloak event-listener
  // bridge that auto-provisions PDS accounts and surfaces the
  // synthesised app-password to the user. RBAC is intentionally not
  // mappable: the PDS only knows "account exists / does not exist".
  // The exceptions are documented in README.md per requirement 013.
  const response = await page.goto(`${baseUrl}/`);
  expect(response, "Expected bluesky response").toBeTruthy();
  expect(response.status(), "Expected bluesky status < 500").toBeLessThan(500);
  expect(
    response.url().includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" to back the bluesky URL`
  ).toBe(true);
});
