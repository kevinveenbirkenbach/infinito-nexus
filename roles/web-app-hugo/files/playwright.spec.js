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

const appBaseUrl = normalizeBaseUrl(process.env.APP_BASE_URL || "");
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN || "");

test.beforeEach(async ({ page }) => {
  expect(appBaseUrl, "APP_BASE_URL must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  await page.context().clearCookies();
});

test("hugo front page is served under canonical domain with TLS + HSTS", async ({ page }) => {
  const response = await page.goto(`${appBaseUrl}/`);
  expect(response, "Expected hugo response").toBeTruthy();
  expect(response.status(), "Expected hugo front page status < 400").toBeLessThan(400);
  expect(
    response.url().includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" to back the hugo URL`
  ).toBe(true);
  const headers = response.headers();
  expect(headers["strict-transport-security"], "hugo must emit HSTS").toBeTruthy();
});

test("hugo emits a CSP header on the front page", async ({ request }) => {
  const response = await request.get(`${appBaseUrl}/`);
  expect(response.status(), "Expected hugo front page status < 400").toBeLessThan(400);
  const headers = response.headers();
  const csp = headers["content-security-policy"];
  expect(
    csp && csp.length > 0,
    `Expected non-empty Content-Security-Policy header, got "${csp || ""}"`
  ).toBe(true);
});

test("hugo serves rendered HTML with a non-empty <title>", async ({ page }) => {
  await page.goto(`${appBaseUrl}/`);
  // Hugo renders a static page; the docs theme always emits a non-empty
  // <title>. This verifies the build pipeline produced a real page, not
  // an nginx default index nor a directory listing.
  const title = await page.title();
  expect(title && title.trim().length > 0, `Expected non-empty <title>, got "${title}"`).toBe(true);
  // The <html> root should be present and the page should NOT contain the
  // BusyBox/nginx default-index marker.
  const body = await page.content();
  expect(body.includes("<html"), "Expected <html> in response body").toBe(true);
  expect(
    body.includes("Welcome to nginx") || body.includes("Index of /"),
    "Expected Hugo content, not the nginx default page or a directory listing"
  ).toBe(false);
});
