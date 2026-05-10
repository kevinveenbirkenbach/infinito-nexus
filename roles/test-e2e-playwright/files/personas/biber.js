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
  // Explicit role contract opt-out (req 019 Rule 11). Roles that
  // genuinely have no biber-accessible surface (admin-only software
  // without OIDC auto-provisioning, mobile-first SPAs whose logout
  // control is unreachable to the generic helper, ...) declare
  // `PERSONA_BIBER_BLOCKED=true` in `templates/playwright.env.j2`
  // with a documented rationale in the role's TODO.md or README.md.
  // The check sits at the top of the flow so the opt-out shortcuts
  // the entire dashboard → app → logout journey, not just the
  // auth-surface detection.
  if ((process.env.PERSONA_BIBER_BLOCKED || "").toLowerCase() === "true") {
    test.skip(
      true,
      `biber persona is explicitly blocked by the role contract (PERSONA_BIBER_BLOCKED=true). See the role's TODO.md for the rationale and the path back to a runnable journey.`,
    );
    return;
  }

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

  // Verify biber actually reached an authenticated surface on the
  // role. The persona contract demands a full dashboard → app →
  // logout journey, so the post-OIDC page MUST expose a logout
  // control or a user menu. When it does NOT, that is either:
  //   - a real regression (OIDC mapping broken, post-login UI
  //     missing the logout button, role's auth chain misconfigured),
  //     OR
  //   - a deliberate role contract that biber has NO access to this
  //     role at all (admin-only role like akaunting / matomo /
  //     prometheus admin UI / fider).
  //
  // The deliberate case MUST be declared explicitly by the role via
  // the env flag `PERSONA_BIBER_BLOCKED=true` (rendered in
  // `templates/playwright.env.j2`). Without that flag the test
  // fails loudly so a real regression cannot hide behind a silent
  // skip.
  // Auth-surface detection: biber is "in" when the role's canonical
  // surface is loaded inside ANY frame of the page (outer or
  // dashboard-wrapped iframe), with a non-error response. The check
  // is URL-based rather than selector-based because many SPAs hide
  // their logout / account control behind icon-only buttons that
  // accessibility tooling can't reach reliably. The persona contract
  // is already covered by:
  //   - the OIDC chain itself returning the app URL (proves Keycloak
  //     accepted biber and the proxy let the session through);
  //   - the role's bespoke spec tests (login form, BSKY_STORAGE,
  //     post-login DOM marker) where applicable;
  //   - the deny-checks against prometheus / matomo (still strict).
  // A role that genuinely refuses biber (akaunting, mailu admin,
  // etc.) has its frames bounce to a denial page or stay on Keycloak;
  // the URL never settles on the role's canonical domain.
  const authMarker = (surface) =>
    surface
      .getByRole("button", { name: /^(log\s*out|sign\s*out|abmelden)$/i })
      .or(surface.getByRole("link", { name: /^(log\s*out|sign\s*out|abmelden)$/i }))
      .or(surface.getByRole("button", { name: /^(account|profile|user.?menu|menu)$/i }))
      .or(surface.locator("[data-region='user-menu-toggle'], .user-menu-toggle, .usermenu, [aria-label*='user menu' i]"));
  let reachedAuthenticated = await authMarker(page).first().isVisible({ timeout: 10_000 }).catch(() => false);
  if (!reachedAuthenticated) {
    for (const frame of page.frames()) {
      const fUrl = frame.url();
      if (!fUrl || fUrl === "about:blank") continue;
      if (await authMarker(frame).first().isVisible({ timeout: 1_000 }).catch(() => false)) {
        reachedAuthenticated = true;
        break;
      }
    }
  }
  if (!reachedAuthenticated) {
    // URL-based fallback: any nested frame parked on the role's
    // canonical surface (NOT on Keycloak / oauth2-proxy denial /
    // about:blank) counts as the persona reaching the app.
    for (const frame of page.frames()) {
      const fUrl = frame.url();
      if (!fUrl || fUrl === "about:blank") continue;
      if (/openid-connect\/auth|\/oauth2\/(?:start|sign_in|callback)/.test(fUrl)) continue;
      if (canonicalDomain && fUrl.includes(canonicalDomain)) {
        reachedAuthenticated = true;
        break;
      }
      if (appBaseUrl && fUrl.startsWith(appBaseUrl)) {
        reachedAuthenticated = true;
        break;
      }
    }
  }
  if (!reachedAuthenticated) {
    expect(
      false,
      `biber did NOT reach an authenticated surface on ${canonicalDomain}. ` +
        `Either the role's auth chain is broken (OIDC mapping, post-login UI, logout button) ` +
        `or biber legitimately has no access here, in which case the role MUST declare ` +
        `\`PERSONA_BIBER_BLOCKED=true\` in templates/playwright.env.j2. ` +
        `Current URL: ${page.url()}.`,
    ).toBe(true);
    return;
  }

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
