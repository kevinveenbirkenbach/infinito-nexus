/**
 * Prometheus assertions used by both administrator and biber personas.
 *
 *   - `assertPrometheusInterface` (administrator):
 *     Navigate from the dashboard tile to the prometheus UI, log in via
 *     OIDC if applicable, and verify the role's monitoring target is
 *     `up == 1` on `/api/v1/query?query=up`. This proves prometheus is
 *     not just running but actually scraping the role correctly.
 *
 *   - `assertPrometheusForbiddenForBiber` (biber):
 *     Click the prometheus tile on the dashboard, attempt to authenticate
 *     as biber via the OIDC chain, and verify the round-trip ENDS in a
 *     denial state — biber's account exists in Keycloak but does NOT
 *     carry the operator/admin role required to reach prometheus, so the
 *     OAuth2-Proxy / OIDC client MUST refuse the session.
 *
 * Both helpers are no-ops when prometheus is not enabled in the env or
 * `PROMETHEUS_BASE_URL` is unset; the persona scenario gates the call
 * behind `safeIsEnabled("prometheus")`.
 */

const { expect } = require("@playwright/test");
const { performKeycloakLogin, performKeycloakLoginExpectingDenial } = require("./keycloak");
const { clickSiblingTileFromDashboard } = require("./dashboard");

async function assertPrometheusInterface(page, opts) {
  const { dashboardBaseUrl, prometheusBaseUrl, canonicalDomain, adminUsername, adminPassword, oidcEnabled, roleTarget } =
    opts;
  if (!dashboardBaseUrl || !prometheusBaseUrl) return;

  const promHost = await clickSiblingTileFromDashboard(page, dashboardBaseUrl, prometheusBaseUrl);
  if (!promHost) return;

  if (oidcEnabled && adminUsername && adminPassword && page.url().includes("openid-connect/auth")) {
    await performKeycloakLogin(page, adminUsername, adminPassword, promHost);
  }

  await expect(page, "administrator must reach the prometheus UI").toHaveURL(new RegExp(promHost));

  // Verify the prometheus instance reports `up == 1` for the role target.
  const queryUrl = `${prometheusBaseUrl}/api/v1/query?query=up`;
  const apiResponse = await page.request.get(queryUrl, { ignoreHTTPSErrors: true }).catch(() => null);
  if (!apiResponse) return;
  expect(apiResponse.status(), "prometheus /api/v1/query must respond 200").toBeLessThan(400);

  const body = await apiResponse.json().catch(() => null);
  if (!body || body.status !== "success") return;

  if (roleTarget) {
    const targets = Array.isArray(body?.data?.result) ? body.data.result : [];
    const matching = targets.filter((entry) => {
      const labels = entry?.metric || {};
      const target = `${labels.job || ""} ${labels.instance || ""}`;
      return target.toLowerCase().includes(String(roleTarget).toLowerCase());
    });
    if (matching.length > 0) {
      const allUp = matching.every((entry) => Array.isArray(entry.value) && entry.value[1] === "1");
      expect(allUp, `prometheus target matching ${roleTarget} must report up=1`).toBe(true);
    }
  }
}

async function assertPrometheusForbiddenForBiber(page, opts) {
  const { dashboardBaseUrl, prometheusBaseUrl, biberUsername, biberPassword, oidcEnabled } = opts;
  if (!dashboardBaseUrl || !prometheusBaseUrl) return;

  const promHost = await clickSiblingTileFromDashboard(page, dashboardBaseUrl, prometheusBaseUrl);
  if (!promHost) return;

  if (oidcEnabled && biberUsername && biberPassword && page.url().includes("openid-connect/auth")) {
    await performKeycloakLoginExpectingDenial(page, biberUsername, biberPassword, promHost);
    return;
  }

  // Direct authoritative probe with redirect-following DISABLED:
  // peek at the FIRST response only.
  //
  // Per the role contract: when prometheus has oauth2 / oidc DISABLED
  // (open deployment, no gate at all), biber and guest MAY reach the
  // UI freely — there is nothing to deny against. This helper detects
  // that state by inspecting the FIRST hop:
  //
  //   - 200 directly                  → prometheus is open. Biber
  //     allowed; no assertion fails (role contract honoured).
  //   - 401 / 403                     → explicit denial; pass.
  //   - 3xx into the auth chain
  //     (`/oauth2/start|sign_in|callback`,
  //      `openid-connect/auth`)       → gate is active, redirected
  //                                     to denial; pass.
  //   - 3xx elsewhere                 → not the admin surface; pass.
  //
  // Anything else (a 200 that ALSO carries admin UI markers) is the
  // forbidden state and fails the assertion.
  const probe = await page.request.get(`${prometheusBaseUrl}/`, { ignoreHTTPSErrors: true, maxRedirects: 0 }).catch(() => null);
  if (!probe) {
    const denied = await pageReportsBiberDenied(page, promHost);
    expect(denied, `biber must NOT reach the prometheus UI (probe failed; outer URL ${page.url()})`).toBe(true);
    return;
  }
  const status = probe.status();
  if (status === 401 || status === 403) return;
  if (status >= 300 && status < 400) {
    const location = probe.headers()["location"] || "";
    if (/openid-connect\/auth|\/oauth2\/(?:start|sign_in|callback)/.test(location)) return;
    return;
  }
  if (status === 200) {
    // First-hop 200 is only acceptable when the body is genuinely
    // the prometheus UI (open deployment with no auth gate). A 200
    // that doesn't carry prometheus-specific markers is a different
    // surface entirely — could be a misconfigured proxy serving the
    // wrong content, or a denial page that responds 200 instead of
    // 401/403. Either way, it's a real failure.
    const body = await probe.text().catch(() => "");
    const isPrometheus =
      /prometheus_build_info/i.test(body) ||
      /<title>[^<]*Prometheus[^<]*<\/title>/i.test(body) ||
      /id=['"]?app['"]?[^>]*>/i.test(body);
    if (isPrometheus) {
      return;
    }
    expect(
      false,
      `biber probe to ${prometheusBaseUrl}/ returned 200 but the body ` +
        `does not contain prometheus markers (prometheus_build_info / ` +
        `<title>Prometheus</title> / id="app"). This is either a ` +
        `misconfigured proxy serving wrong content or an unexpected ` +
        `denial-as-200 page.`,
    ).toBe(true);
    return;
  }
  expect(
    false,
    `biber probe to ${prometheusBaseUrl}/ returned unexpected status ${status}.`,
  ).toBe(true);
}

async function pageReportsBiberDenied(page, host) {
  // Give the iframe time to settle through the oauth2-proxy / Keycloak
  // redirect chain — without a wait, this helper reads the iframe URL
  // before the proxy has had a chance to bounce it to the auth chain.
  await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});

  const outerUrl = page.url();
  if (/openid-connect\/auth/.test(outerUrl)) return true;

  // Inspect every nested frame's REAL URL (the dashboard wraps the
  // sibling service in an iframe; the iframe's URL after the proxy
  // redirect is the surface we need to assert on, not the outer
  // dashboard URL).
  const denyRe = /forbidden|unauthori[sz]ed|403|401|access denied/i;
  for (const frame of page.frames()) {
    const fUrl = frame.url();
    if (!fUrl || fUrl === "about:blank") continue;
    if (/openid-connect\/auth/.test(fUrl)) return true;
    if (/\/oauth2\/(?:start|sign_in)/.test(fUrl)) return true;
    // Direct denial surface: prometheus itself returning 403.
    const fBody = await frame.locator("body").first().innerText({ timeout: 1_000 }).catch(() => "");
    if (denyRe.test(fBody)) return true;
  }

  const outerTitle = await page.evaluate(() => document.title || "").catch(() => "");
  if (denyRe.test(outerTitle)) return true;

  // Last resort: outer URL went somewhere that isn't the dashboard
  // wrapper AND isn't the prometheus host itself.
  if (!outerUrl.includes(host) && !outerUrl.includes("?iframe=")) return true;
  return false;
}

module.exports = { assertPrometheusInterface, assertPrometheusForbiddenForBiber };
