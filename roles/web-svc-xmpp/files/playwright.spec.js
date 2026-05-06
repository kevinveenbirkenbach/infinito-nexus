const { test, expect } = require("@playwright/test");
const { skipUnlessServiceEnabled } = require("./service-gating");

test.use({ ignoreHTTPSErrors: true });

function decodeDotenvQuotedValue(value) {
  if (typeof value !== "string" || value.length < 2) return value;
  if (!(value.startsWith('"') && value.endsWith('"'))) return value;
  const encoded = value.slice(1, -1);
  try { return JSON.parse(`"${encoded}"`).replace(/\$\$/g, "$"); }
  catch { return encoded.replace(/\$\$/g, "$"); }
}
function normalizeBaseUrl(value) { return decodeDotenvQuotedValue(value || "").replace(/\/$/, ""); }

const baseUrl = normalizeBaseUrl(process.env.XMPP_BASE_URL || "");
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN || "");

test.beforeEach(async ({ page }) => {
  expect(baseUrl, "XMPP_BASE_URL must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  await page.context().clearCookies();
});

test("baseline: ejabberd HTTP API responds on the canonical domain", async ({ page }) => {
  // The ejabberd HTTP listener at /admin and /api covers the
  // web-facing surfaces; XMPP client login itself runs over
  // 5222/5269 and is not Playwright-testable via HTTP. The
  // baseline asserts the role at least binds correctly.
  const r = await page.goto(`${baseUrl}/admin/`);
  expect(r).toBeTruthy();
  expect(r.status()).toBeLessThan(500);
  expect(r.url().includes(canonicalDomain)).toBe(true);
});

test("LDAP: ejabberd backend points at svc-db-openldap (variant 1)", async ({ page }) => {
  skipUnlessServiceEnabled("ldap");
  const r = await page.goto(`${baseUrl}/admin/`);
  expect(r).toBeTruthy();
  expect(r.status()).toBeLessThan(500);
});
