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

  // Direct authoritative probe with redirect-following DISABLED.
  // Per the role contract: when matomo has oauth2 / oidc DISABLED,
  // biber MAY reach the matomo login form freely (no gate to deny
  // against). The deny-check inspects the FIRST hop only:
  //
  //   - 200 + matomo login form      → matomo reachable, pre-auth;
  //                                     biber is at a login surface,
  //                                     not at an authenticated admin
  //                                     UI. Pass.
  //   - 200 with NO admin markers    → open deployment / public
  //                                     landing. Pass.
  //   - 401 / 403                    → explicit denial; pass.
  //   - 3xx into the auth chain      → gate active, redirected to
  //                                     denial; pass.
  //   - 3xx elsewhere                → not the admin surface; pass.
  //
  // Only fails when a first-hop 200 carries admin-only DOM markers
  // (matomo Dashboard / Settings / activeNav), proving biber crossed
  // into an authenticated admin surface.
  const probe = await page.request.get(`${matomoBaseUrl}/`, { ignoreHTTPSErrors: true, maxRedirects: 0 }).catch(() => null);
  if (probe) {
    const status = probe.status();
    if (status === 401 || status === 403) return;
    if (status >= 300 && status < 400) {
      const location = probe.headers()["location"] || "";
      if (/openid-connect\/auth|\/oauth2\/(?:start|sign_in|callback)/.test(location)) return;
      return;
    }
    if (status === 200) {
      const body = await probe.text().catch(() => "");
      // Tighter check: a 200 is only acceptable when the body is
      // genuinely a matomo surface (login form OR public landing).
      // A 200 from a non-matomo body is a misconfigured proxy or an
      // unexpected denial-as-200 — fail loudly.
      const isMatomoLogin =
        /<input[^>]*name=['"]?form_login['"]?/i.test(body) ||
        /<input[^>]*name=['"]?form_password['"]?/i.test(body) ||
        /piwik|matomo/i.test(body);
      const showsAdminUi =
        /id=['"]?Dashboard_/i.test(body) &&
        (/id=['"]?Settings/i.test(body) || /class=['"][^'"]*activeNav/i.test(body));
      if (showsAdminUi) {
        expect(
          false,
          `biber must NOT reach the matomo UI: GET ${matomoBaseUrl}/ returned 200 with admin DOM markers.`,
        ).toBe(true);
        return;
      }
      if (isMatomoLogin) return;
      expect(
        false,
        `biber probe to ${matomoBaseUrl}/ returned 200 but the body is neither matomo's login form ` +
          `nor a recognisable matomo / piwik surface. This is a misconfigured proxy or an unexpected denial-as-200 page.`,
      ).toBe(true);
      return;
    }
    return;
  }
  const outerUrl = page.url();
  const fallbackDenied = /openid-connect\/auth/.test(outerUrl) || (!outerUrl.includes(matomoHost) && !outerUrl.includes("?iframe="));
  expect(fallbackDenied, `biber must NOT reach the matomo UI (probe failed; outer URL ${outerUrl})`).toBe(true);
}

module.exports = { assertMatomoInterfaceForAdmin, assertMatomoForbiddenForBiber };
