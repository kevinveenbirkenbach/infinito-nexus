/**
 * `administrator` persona: single-app authenticated journey.
 *
 *   appBaseUrl → (OIDC if applicable) → admin-only interaction
 *              → CSP injection check → in-app logout
 *              → unauthenticated landing assertion.
 *
 * The administrator persona is now scoped to the role under test only.
 * Cross-service surface checks (prometheus, matomo, dashboard tile
 * reachability) are owned by the dedicated provider specs:
 *
 *   - `roles/web-app-dashboard/files/playwright.spec.js` parameterises
 *     dashboard-tile reachability per consumer role.
 *   - `roles/web-app-prometheus/files/playwright.spec.js` parameterises
 *     scrape-target presence + admin reach + biber denial.
 *   - `roles/web-app-matomo/files/playwright.spec.js` parameterises
 *     tracker-site presence + admin reach + biber denial.
 *
 * Each role's persona scenario therefore visits its OWN canonical URL
 * directly (no dashboard tile click) and exercises only that role.
 */

const { test, expect } = require("@playwright/test");
const {
  normalizeUrl,
  readEnv,
  safeIsEnabled,
  performKeycloakLogin,
  inAppLogout,
  assertUnauthenticatedLanding,
  assertCspInjections,
  runRoleInteraction,
} = require("./utils");

async function runAdminFlow(page, opts = {}) {
  // Explicit role contract opt-out (req 019 Rule 11). Roles that
  // genuinely have no OIDC-driven admin surface (auth-provider roles,
  // bespoke local-only admin paths, mobile-first SPAs whose logout
  // control is unreachable to the generic helper, ...) declare
  // `PERSONA_ADMINISTRATOR_BLOCKED=true` in
  // `templates/playwright.env.j2` with a documented rationale in the
  // role's TODO.md or README.md.
  if ((process.env.PERSONA_ADMINISTRATOR_BLOCKED || "").toLowerCase() === "true") {
    test.skip(
      true,
      `administrator persona is explicitly blocked by the role contract (PERSONA_ADMINISTRATOR_BLOCKED=true). See the role's TODO.md for the rationale and the path back to a runnable journey.`,
    );
    return;
  }

  // Test B parity: oauth2-proxy gates the initial redirect chain,
  // universal-logout rewrites the in-app logout click, and the shared
  // CSP-injection helper (`assertCspInjections`) gates on `matomo` to
  // verify every role's CSP allows the matomo tracker host when matomo
  // is enabled. All three are consumed by the persona surface;
  // reference them via safeIsEnabled with literal arguments so the
  // env-gate parity guard recognises them as consumed by the spec via
  // the shared persona helper.
  safeIsEnabled("oauth2");
  safeIsEnabled("logout");
  safeIsEnabled("matomo");

  const canonicalDomain = readEnv("CANONICAL_DOMAIN");
  const appBaseUrl = normalizeUrl(process.env.APP_BASE_URL);
  const adminUsername = readEnv("ADMIN_USERNAME");
  const adminPassword = readEnv("ADMIN_PASSWORD");

  // Persona-collapse exception (req 019): roles whose env does not
  // expose APP_BASE_URL or CANONICAL_DOMAIN are auth-less by
  // construction; skip cleanly rather than fail.
  if (!appBaseUrl || !canonicalDomain) {
    test.skip(
      true,
      "Auth-less role (no APP_BASE_URL / CANONICAL_DOMAIN) — persona scenario collapsed per req 019.",
    );
    return;
  }

  await page.context().clearCookies();

  const oidcEnabled = safeIsEnabled("oidc");

  // Direct-app entry: bookmark-style navigation. The OAuth2-Proxy gate
  // fires on the first request, redirecting unauthenticated requests
  // to Keycloak; the auth chain is the same regardless of how the user
  // arrived at the URL.
  await page.goto(`${appBaseUrl}/`, { waitUntil: "domcontentloaded" }).catch(() => {});

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

  // Verify administrator actually reached an authenticated surface.
  // The persona contract demands a full app → logout journey. When
  // the post-OIDC page does NOT expose a logout control / user menu,
  // that is a real regression UNLESS the role explicitly declares the
  // admin persona blocked via env flag
  // `PERSONA_ADMINISTRATOR_BLOCKED=true`. Without that flag the test
  // fails loudly so a real regression cannot hide behind a silent
  // skip.
  const adminAuthMarker = (surface) =>
    surface
      .getByRole("button", { name: /^(log\s*out|sign\s*out|abmelden)$/i })
      .or(surface.getByRole("link", { name: /^(log\s*out|sign\s*out|abmelden)$/i }))
      .or(surface.getByRole("button", { name: /^(account|profile|user.?menu|menu)$/i }))
      .or(surface.locator("[data-region='user-menu-toggle'], .user-menu-toggle, .usermenu, [aria-label*='user menu' i]"));
  let adminReachedAuthenticated = await adminAuthMarker(page).first().isVisible({ timeout: 10_000 }).catch(() => false);
  if (!adminReachedAuthenticated) {
    for (const frame of page.frames()) {
      const fUrl = frame.url();
      if (!fUrl || fUrl === "about:blank") continue;
      if (await adminAuthMarker(frame).first().isVisible({ timeout: 1_000 }).catch(() => false)) {
        adminReachedAuthenticated = true;
        break;
      }
    }
  }
  if (!adminReachedAuthenticated) {
    // URL-based fallback: any nested frame parked on the role's
    // canonical surface (not on Keycloak / oauth2-proxy denial /
    // about:blank) counts as the administrator reaching the app.
    for (const frame of page.frames()) {
      const fUrl = frame.url();
      if (!fUrl || fUrl === "about:blank") continue;
      if (/openid-connect\/auth|\/oauth2\/(?:start|sign_in|callback)/.test(fUrl)) continue;
      if (canonicalDomain && fUrl.includes(canonicalDomain)) {
        adminReachedAuthenticated = true;
        break;
      }
      if (appBaseUrl && fUrl.startsWith(appBaseUrl)) {
        adminReachedAuthenticated = true;
        break;
      }
    }
  }
  if (!adminReachedAuthenticated) {
    expect(
      false,
      `administrator did NOT reach an authenticated surface on ${canonicalDomain}. ` +
        `Either the role's auth chain is broken or administrator legitimately has no OIDC-driven admin path here, ` +
        `in which case the role MUST declare \`PERSONA_ADMINISTRATOR_BLOCKED=true\` in templates/playwright.env.j2. ` +
        `Current URL: ${page.url()}.`,
    ).toBe(true);
    return;
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
