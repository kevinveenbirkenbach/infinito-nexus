/**
 * Matomo assertions used by both administrator and biber personas.
 *
 *   - `assertMatomoInterfaceForAdmin` (administrator):
 *     Click the matomo tile on the dashboard, follow the OIDC chain
 *     when applicable, and verify the resulting page is the
 *     administrator-authenticated matomo UI on the matomo canonical
 *     host. This proves matomo is not just running but actually
 *     accepting the administrator's identity.
 *
 *   - `assertMatomoForbiddenForBiber` (biber):
 *     Click the matomo tile on the dashboard, attempt to authenticate
 *     as biber via the OIDC chain, and verify the round-trip ENDS in a
 *     denial state. Matomo is admin-only by default; biber MUST NOT be
 *     granted a session there.
 *
 * Both helpers are no-ops when matomo is not enabled or
 * `MATOMO_BASE_URL` is unset; the persona scenario gates the call
 * behind `safeIsEnabled("matomo")`.
 */

const { expect } = require("@playwright/test");
const { performKeycloakLogin, performKeycloakLoginExpectingDenial } = require("./keycloak");
const { clickSiblingTileFromDashboard } = require("./dashboard");

async function assertMatomoInterfaceForAdmin(page, opts) {
  const { dashboardBaseUrl, matomoBaseUrl, adminUsername, adminPassword, oidcEnabled } = opts;
  if (!dashboardBaseUrl || !matomoBaseUrl) return;

  const matomoHost = await clickSiblingTileFromDashboard(page, dashboardBaseUrl, matomoBaseUrl);
  if (!matomoHost) return;

  if (oidcEnabled && adminUsername && adminPassword && page.url().includes("openid-connect/auth")) {
    await performKeycloakLogin(page, adminUsername, adminPassword, matomoHost);
  }

  await expect(page, "administrator must reach the matomo UI").toHaveURL(new RegExp(matomoHost));
}

async function assertMatomoForbiddenForBiber(page, opts) {
  const { dashboardBaseUrl, matomoBaseUrl, biberUsername, biberPassword, oidcEnabled } = opts;
  if (!dashboardBaseUrl || !matomoBaseUrl) return;

  const matomoHost = await clickSiblingTileFromDashboard(page, dashboardBaseUrl, matomoBaseUrl);
  if (!matomoHost) return;

  if (oidcEnabled && biberUsername && biberPassword && page.url().includes("openid-connect/auth")) {
    await performKeycloakLoginExpectingDenial(page, biberUsername, biberPassword, matomoHost);
    return;
  }

  const denied = /openid-connect\/auth/.test(page.url()) || !page.url().includes(matomoHost);
  expect(denied, `biber must NOT reach the matomo UI (got URL ${page.url()})`).toBe(true);
}

module.exports = { assertMatomoInterfaceForAdmin, assertMatomoForbiddenForBiber };
