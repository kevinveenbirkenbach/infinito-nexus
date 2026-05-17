const { test, expect } = require("@playwright/test");

const { decodeDotenvQuotedValue } = require("./personas");

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

// Accepts any `<link rel="stylesheet" href="…">` whose URL host matches
// one of the shared CSS asset hosts. Catches the regression where
// sys-front-inj-css is not wired into a consumer's vhost or where
// services.css.{enabled,shared} mismatch `'web-svc-css' in group_names`.
function htmlIndexesSharedCssLink(html) {
  if (!html || typeof html !== "string") return false;
  const linkRe = /<link\b[^>]*\brel=["']stylesheet["'][^>]*\bhref=["']([^"']+)["'][^>]*>/gi;
  let match;
  while ((match = linkRe.exec(html)) !== null) {
    try {
      const candidate = new URL(match[1], "https://example.com/");
      if (cssAssetHosts.includes(candidate.host.toLowerCase())) return true;
    } catch {
      // Skip unparseable href values; keep scanning.
    }
  }
  return false;
}

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
// Per-consumer CSS indexing: one parameterised assertion per role
// declared as a css consumer in its meta/services.yml. The role list
// is emitted into CSS_TARGET_ROLES_JSON at deploy time via the
// `roles_with_service('css')` Ansible lookup, so this spec — and
// ONLY this spec — owns the consumer-side `<link rel="stylesheet">`
// check. Consumer roles suppress the env-services match guard with
// `# nocheck: playwright-service-flag — verified by web-svc-css provider spec`.
// -----------------------------------------------------------------------------

for (const target of cssTargetRoles) {
  test(`css: ${target.id} canonical surface indexes shared CSS asset`, async ({ request }) => {
    const url = `${target.canonical_url.replace(/\/$/, "")}/`;
    const res = await request.get(url, { ignoreHTTPSErrors: true });

    expect(
      res.status(),
      `${target.id}: GET ${url} returned ${res.status()} — surface must be reachable for the CSS-injection assertion to be meaningful`
    ).toBeLessThan(500);

    const body = await res.text();
    expect(
      htmlIndexesSharedCssLink(body),
      `${target.id}: HTML response from ${url} does not contain a ` +
      `<link rel="stylesheet" href="..."> targeting one of the shared ` +
      `CSS asset hosts [${cssAssetHosts.join(", ")}]. ` +
      `Verify sys-front-inj-css is wired into the role's vhost and ` +
      `that services.css.{enabled,shared} match 'web-svc-css' in ` +
      `group_names for the inventory under test.`
    ).toBe(true);
  });
}
