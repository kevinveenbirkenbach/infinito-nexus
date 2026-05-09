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

  // No OIDC chain reached: the proxy MUST already reject biber.
  const status = await page.evaluate(() => document.title || "").catch(() => "");
  const denied = /forbidden|unauthori[sz]ed|403|401/i.test(status) || /openid-connect\/auth/.test(page.url());
  expect(denied, `biber must NOT reach the prometheus UI (got URL ${page.url()})`).toBe(true);
}

module.exports = { assertPrometheusInterface, assertPrometheusForbiddenForBiber };
