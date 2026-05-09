/**
 * `administrator` persona: multi-app round-trip.
 *
 * dashboard → (gated) prometheus interface check → back to dashboard
 *           → (gated) matomo interface login → back to dashboard
 *           → click role tile → admin auth (OIDC if applicable)
 *           → CSP injection check
 *           → in-app logout → unauthenticated landing assertion.
 *
 * The prometheus and matomo sub-flows prove that the administrator
 * identity is accepted by the operator-only sibling services (the
 * counter-assertion to biber's deny checks).
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
  assertPrometheusInterface,
  assertMatomoInterfaceForAdmin,
  runRoleInteraction,
} = require("./utils");

async function runAdminFlow(page, opts = {}) {
  if (!opts.skipDashboardGate) safeSkipUnlessEnabled("dashboard");

  // Test B parity: oauth2-proxy gates the initial redirect chain,
  // universal-logout rewrites the in-app logout click. Both are
  // consumed by the persona surface; reference them via safeIsEnabled
  // so the env-gate parity guard recognises them as consumed by the
  // spec via the shared persona helper.
  safeIsEnabled("oauth2");
  safeIsEnabled("logout");

  const dashboardBaseUrl = normalizeUrl(process.env.DASHBOARD_BASE_URL);
  const prometheusBaseUrl = normalizeUrl(process.env.PROMETHEUS_BASE_URL);
  const matomoBaseUrl = normalizeUrl(process.env.MATOMO_BASE_URL);
  const canonicalDomain = readEnv("CANONICAL_DOMAIN");
  const appBaseUrl = normalizeUrl(process.env.APP_BASE_URL);
  const adminUsername = readEnv("ADMIN_USERNAME");
  const adminPassword = readEnv("ADMIN_PASSWORD");
  const roleTarget = readEnv("PROMETHEUS_TARGET_HINT") || canonicalDomain;

  // Persona-collapse exception (req 019): roles whose env does not
  // expose DASHBOARD_BASE_URL or CANONICAL_DOMAIN are auth-less by
  // construction; skip cleanly rather than fail.
  if (!dashboardBaseUrl || !canonicalDomain) {
    test.skip(
      true,
      "Auth-less role (no DASHBOARD_BASE_URL / CANONICAL_DOMAIN) — persona scenario collapsed per req 019.",
    );
    return;
  }

  await page.context().clearCookies();

  const oidcEnabled = safeIsEnabled("oidc");

  if (safeIsEnabled("prometheus")) {
    await assertPrometheusInterface(page, {
      dashboardBaseUrl,
      prometheusBaseUrl,
      canonicalDomain,
      adminUsername,
      adminPassword,
      oidcEnabled,
      roleTarget,
    });
    await page.context().clearCookies();
  }

  if (safeIsEnabled("matomo")) {
    await assertMatomoInterfaceForAdmin(page, {
      dashboardBaseUrl,
      matomoBaseUrl,
      adminUsername,
      adminPassword,
      oidcEnabled,
    });
    await page.context().clearCookies();
  }

  await clickRoleTileFromDashboard(page, dashboardBaseUrl, canonicalDomain);

  if (oidcEnabled && adminUsername && adminPassword) {
    const loginLink = page
      .getByRole("link", { name: /^(log\s*in|sign\s*in|login|sso|admin)$/i })
      .or(page.getByRole("button", { name: /^(log\s*in|sign\s*in|login|sso|admin)$/i }))
      .first();
    if (await loginLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await loginLink.click().catch(() => {});
    }
    if (page.url().includes("openid-connect/auth")) {
      await performKeycloakLogin(page, adminUsername, adminPassword, canonicalDomain);
    }
  }

  await assertCspInjections(page, { isEnabled: safeIsEnabled });

  // Drive a real, app-specific interaction after login. Specs SHOULD
  // override the default by passing an `adminInteraction` callback that
  // exercises an admin-only surface (admin panel, realm settings, ...).
  await runRoleInteraction(page, { canonicalDomain, roleInteraction: opts.adminInteraction });

  await inAppLogout(page);
  await assertUnauthenticatedLanding(page, appBaseUrl);
}

module.exports = { runAdminFlow };
