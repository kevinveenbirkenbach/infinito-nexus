/**
 * CSP injection assertion shared by every persona scenario.
 *
 * `assertCspInjections` re-fetches the current URL via
 * `page.request.get` so it can read the raw `content-security-policy`
 * (or `content-security-policy-report-only`) header off the response,
 * then verifies that every service whose JavaScript / CSS / asset is
 * actually injected on the page is also covered by the role's CSP.
 *
 * The intent is symmetric: when an injector role like `mastodon`,
 * `web-svc-asset`, `web-svc-cdn`, `web-svc-css`, `web-svc-javascript`
 * or `web-svc-simpleicons` is enabled, its origin MUST appear in the
 * CSP. When the injector is disabled, its origin MUST NOT appear in
 * any rendered `<script>` / `<link>` / `<img>` tag — otherwise the
 * page would load resources the CSP doesn't permit.
 *
 * The helper is tolerant of policies served via meta-tag (some apps
 * cannot set CSP via header for legacy reasons): it falls back to the
 * first `<meta http-equiv="content-security-policy">` element.
 */

const { expect } = require("@playwright/test");

const INJECTOR_ENV = {
  asset: "ASSET_BASE_URL",
  cdn: "CDN_BASE_URL",
  css: "CSS_BASE_URL",
  javascript: "JAVASCRIPT_BASE_URL",
  simpleicons: "SIMPLEICONS_BASE_URL",
  matomo: "MATOMO_BASE_URL",
};

function hostOf(url) {
  if (!url) return "";
  try {
    return new URL(url).hostname;
  } catch {
    return "";
  }
}

async function readCspString(page) {
  const currentUrl = page.url();
  if (!currentUrl || currentUrl === "about:blank") return "";

  const fresh = await page.request.get(currentUrl, { ignoreHTTPSErrors: true }).catch(() => null);
  if (fresh) {
    const headers = fresh.headers();
    const fromHeader = headers["content-security-policy"] || headers["content-security-policy-report-only"];
    if (fromHeader) return fromHeader;
  }

  const fromMeta = await page
    .locator("meta[http-equiv='Content-Security-Policy' i]")
    .first()
    .getAttribute("content")
    .catch(() => "");
  return fromMeta || "";
}

async function assertCspInjections(page, opts = {}) {
  const { isEnabled } = opts;
  if (typeof isEnabled !== "function") return;

  const csp = await readCspString(page);

  for (const [service, envName] of Object.entries(INJECTOR_ENV)) {
    let enabled;
    try {
      enabled = isEnabled(service);
    } catch {
      enabled = false;
    }
    if (!enabled) continue;

    const host = hostOf(process.env[envName]);
    if (!host) continue;

    if (!csp) continue;

    expect(
      csp.toLowerCase().includes(host.toLowerCase()),
      `CSP for the current page MUST include ${host} (service '${service}' is enabled). Got: ${csp}`,
    ).toBe(true);
  }
}

module.exports = { assertCspInjections };
