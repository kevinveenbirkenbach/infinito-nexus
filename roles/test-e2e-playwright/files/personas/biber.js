/**
 * `biber` persona: single-app journey + cross-service deny-checks.
 *
 * dashboard → click role tile → role auth (OIDC if applicable)
 *           → CSP injection check
 *           → (gated) navigate to prometheus tile, expect deny
 *           → (gated) navigate to matomo tile, expect deny
 *           → in-app logout → unauthenticated landing assertion.
 *
 * The deny-checks prove that biber's OIDC account does NOT carry the
 * operator/admin claims required to enter the prometheus or matomo
 * admin surfaces. Biber MUST be a regular end-user identity in the
 * Keycloak realm; matomo and prometheus are admin-only by default.
 */

const { test, expect } = require("@playwright/test");
const {
  normalizeUrl,
  readEnv,
  safeSkipUnlessEnabled,
  safeIsEnabled,
  performKeycloakLogin,
  clickRoleTileFromDashboard,
  inAppLogout,
  assertUnauthenticatedLanding,
  assertCspInjections,
  assertPrometheusForbiddenForBiber,
  assertMatomoForbiddenForBiber,
  runRoleInteraction,
} = require("./utils");

async function runBiberFlow(page, opts = {}) {
  if (!opts.skipDashboardGate) safeSkipUnlessEnabled("dashboard");

  // Test B parity: every role's env declares OAUTH2/LOGOUT_SERVICE_ENABLED
  // (the auth chain runs through oauth2-proxy, the post-flow universal-
  // logout JS rewrites the role's own logout button). Both flags are
  // genuinely consumed by the persona surface — oauth2-proxy gates the
  // initial redirect, universal-logout rewrites the in-app logout
  // click. Reference them via safeIsEnabled so the env-gate parity guard
  // recognises them as consumed by the spec via the shared persona.
  safeIsEnabled("oauth2");
  safeIsEnabled("logout");

  const dashboardBaseUrl = normalizeUrl(process.env.DASHBOARD_BASE_URL);
  const prometheusBaseUrl = normalizeUrl(process.env.PROMETHEUS_BASE_URL);
  const matomoBaseUrl = normalizeUrl(process.env.MATOMO_BASE_URL);
  const canonicalDomain = readEnv("CANONICAL_DOMAIN");
  const appBaseUrl = normalizeUrl(process.env.APP_BASE_URL);
  const biberUsername = readEnv("BIBER_USERNAME");
  const biberPassword = readEnv("BIBER_PASSWORD");

  // Persona-collapse exception (req 019): roles whose env does not
  // expose DASHBOARD_BASE_URL or CANONICAL_DOMAIN are auth-less by
  // construction (web-svc-*, federation-only web-app-*); the persona
  // scenario MUST skip cleanly rather than fail.
  if (!dashboardBaseUrl || !canonicalDomain) {
    test.skip(
      true,
      "Auth-less role (no DASHBOARD_BASE_URL / CANONICAL_DOMAIN) — persona scenario collapsed per req 019.",
    );
    return;
  }

  await page.context().clearCookies();
  await clickRoleTileFromDashboard(page, dashboardBaseUrl, canonicalDomain);

  const oidcEnabled = safeIsEnabled("oidc");

  if (oidcEnabled && biberUsername && biberPassword) {
    const loginLink = page
      .getByRole("link", { name: /^(log\s*in|sign\s*in|login|sso)$/i })
      .or(page.getByRole("button", { name: /^(log\s*in|sign\s*in|login|sso)$/i }))
      .first();
    if (await loginLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await loginLink.click().catch(() => {});
    }
    if (page.url().includes("openid-connect/auth")) {
      await performKeycloakLogin(page, biberUsername, biberPassword, canonicalDomain);
    }
  }

  await assertCspInjections(page, { isEnabled: safeIsEnabled });

  // Drive a real, app-specific interaction after login (or directly on
  // the role surface when no auth is required). Specs SHOULD override
  // the default by passing a `roleInteraction` callback that exercises
  // the role's bespoke UI (post a message, open a settings tab, etc.).
  await runRoleInteraction(page, { canonicalDomain, roleInteraction: opts.biberInteraction });

  if (safeIsEnabled("prometheus")) {
    await assertPrometheusForbiddenForBiber(page, {
      dashboardBaseUrl,
      prometheusBaseUrl,
      biberUsername,
      biberPassword,
      oidcEnabled,
    });
    await page.context().clearCookies();
    // Re-establish biber session before continuing the role flow.
    await clickRoleTileFromDashboard(page, dashboardBaseUrl, canonicalDomain);
    if (oidcEnabled && biberUsername && biberPassword && page.url().includes("openid-connect/auth")) {
      await performKeycloakLogin(page, biberUsername, biberPassword, canonicalDomain);
    }
  }

  if (safeIsEnabled("matomo")) {
    await assertMatomoForbiddenForBiber(page, {
      dashboardBaseUrl,
      matomoBaseUrl,
      biberUsername,
      biberPassword,
      oidcEnabled,
    });
    await page.context().clearCookies();
    await clickRoleTileFromDashboard(page, dashboardBaseUrl, canonicalDomain);
    if (oidcEnabled && biberUsername && biberPassword && page.url().includes("openid-connect/auth")) {
      await performKeycloakLogin(page, biberUsername, biberPassword, canonicalDomain);
    }
  }

  await inAppLogout(page);
  await assertUnauthenticatedLanding(page, appBaseUrl);
}

module.exports = { runBiberFlow };
