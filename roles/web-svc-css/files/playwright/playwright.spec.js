const { test, expect } = require("@playwright/test");

const { assertInjectedAssetLoadsWithoutCspBlock, decodeDotenvQuotedValue } = require("./personas");

test.use({ ignoreHTTPSErrors: true });

const cssBaseUrl = decodeDotenvQuotedValue(process.env.CSS_BASE_URL || "");
const cdnBaseUrl = decodeDotenvQuotedValue(process.env.CDN_BASE_URL || "");

const cssAssetHosts = [cdnBaseUrl, cssBaseUrl]
  .filter(Boolean)
  .map((url) => {
    try {
      return new URL(url).host.toLowerCase();
    } catch {
      return null;
    }
  })
  .filter(Boolean);

const cssTargetRoles = (() => {
  const raw = process.env.CSS_TARGET_ROLES_JSON || "[]";
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
})();

test.beforeEach(() => {
  expect(
    cssAssetHosts.length,
    "CSS_BASE_URL and/or CDN_BASE_URL must be set in the Playwright env file"
  ).toBeGreaterThan(0);
});

// Baseline: the CDN host itself must be reachable so a per-consumer
// failure below unambiguously points at the consumer's injection
// wiring rather than at the asset provider being down.
test("css: shared CSS asset host is reachable", async ({ request }) => {
  const cdnBase = cdnBaseUrl.replace(/\/$/, "");
  const res = await request.get(`${cdnBase}/`, { ignoreHTTPSErrors: true });
  expect(
    res.status(),
    `GET ${cdnBase}/ must be reachable for downstream injection assertions (got ${res.status()})`
  ).toBeLessThan(500);
});

// -----------------------------------------------------------------------------
// Per-consumer CSS indexing + load + CSP compliance: one parameterised
// assertion per role declared as a css consumer in its meta/services.yml.
// The role list is emitted into CSS_TARGET_ROLES_JSON at deploy time
// via the `roles_with_service('css')` Ansible lookup, so this spec —
// and ONLY this spec — owns the consumer-side stylesheet assertion.
// Consumer roles suppress the env-services match guard with
// `# nocheck: playwright-service-flag — verified by web-svc-css provider spec`.
//
// Strict criteria (covers the regression where the `<link>` is in the
// HTML but the browser can't actually load the asset):
//   1. The browser observes a successful HTTP 2xx/3xx response for a
//      `stylesheet` resource from one of the shared CSS asset hosts.
//   2. No `securitypolicyviolation` event names a shared CSS asset
//      host as the blocked URI — i.e. CSP `style-src` permits the load.
// -----------------------------------------------------------------------------

for (const target of cssTargetRoles) {
  test(`css: ${target.id} actually loads shared CSS asset without CSP block`, async ({ page }) => {
    const url = `${target.canonical_url.replace(/\/$/, "")}/`;
    await assertInjectedAssetLoadsWithoutCspBlock(page, {
      url,
      hostCandidates: cssAssetHosts,
      resourceTypes: ["stylesheet"],
      label: target.id,
    });
  });
}
