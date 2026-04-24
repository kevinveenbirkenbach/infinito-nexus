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

const cdnBaseUrl = normalizeBaseUrl(process.env.CDN_BASE_URL || "");
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN);

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  expect(cdnBaseUrl, "CDN_BASE_URL must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  await page.context().clearCookies();
});

test("cdn index is served under canonical domain with TLS", async ({ page }) => {
  const response = await page.goto(`${cdnBaseUrl}/`);
  expect(response, "Expected CDN index response").toBeTruthy();
  expect(response.status(), "Expected CDN index status < 400").toBeLessThan(400);
  expect(
    response.url().includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" to back the CDN URL`
  ).toBe(true);
  const headers = response.headers();
  expect(headers["strict-transport-security"], "CDN must emit HSTS").toBeTruthy();
});
