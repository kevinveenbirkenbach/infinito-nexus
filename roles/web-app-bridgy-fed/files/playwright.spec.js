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

test("bridgy-fed responds under canonical domain with TLS", async ({ page }) => {
  // Bridgy Fed serves a 404 on `/` by design: the canonical landing
  // surfaces are the federation-protocol endpoints (e.g. `/robots.txt`,
  // `/.well-known/host-meta`, `/web/<actor>`), not a generic homepage.
  // The deploy contract this role MUST satisfy is that the HTTP server
  // answers on the canonical domain over TLS, regardless of whether
  // the requested path resolves. A 5xx is the only signal of an
  // unhealthy app.
  const response = await page.goto(`${appBaseUrl}/`);
  expect(response, "Expected bridgy-fed response").toBeTruthy();
  expect(response.status(), "Expected bridgy-fed status < 500 (4xx are by design)").toBeLessThan(500);
  expect(
    response.url().includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" to back the bridgy-fed URL`
  ).toBe(true);
});

test("bridgy-fed serves /robots.txt successfully", async ({ request }) => {
  // Bridgy Fed has no local user accounts and authenticates federation
  // peers via their source-platform credentials, so login / logout
  // scenarios are not applicable. The SSO and RBAC exception is
  // documented in README.md per requirement 013 and lifecycle.md.
  // /robots.txt is the canonical "service is alive" probe for this
  // role; the homepage at `/` is a 404 by design.
  const response = await request.get(`${appBaseUrl}/robots.txt`);
  expect(response.status(), "Expected bridgy-fed /robots.txt status < 400").toBeLessThan(400);
});
