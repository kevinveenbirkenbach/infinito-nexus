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
  // Explicit role contract opt-out. Roles that
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

  // Persona-collapse exception: roles whose env does not
  // expose APP_BASE_URL or CANONICAL_DOMAIN are auth-less by
  // construction; skip cleanly rather than fail.
  if (!appBaseUrl || !canonicalDomain) {
    test.skip(
      true,
      "Auth-less role (no APP_BASE_URL / CANONICAL_DOMAIN) — persona scenario collapsed.",
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

  // Two auth shapes share a single login step:
  //   * oauth2-proxy gate: the goto is intercepted and the page lands
  //     directly on the Keycloak auth endpoint; perform Keycloak login.
  //   * In-app OIDC plugin: the role's own UI exposes a Login link;
  //     click it to trigger the redirect, then perform Keycloak login.
  if (adminUsername && adminPassword) {
    if (oidcEnabled && !page.url().includes("openid-connect/auth")) {
      const loginLink = page
        .getByRole("link", { name: /^\s*(log\s*in|sign\s*in|login|sso|admin)\s*$/i })
        .or(page.getByRole("button", { name: /^\s*(log\s*in|sign\s*in|login|sso|admin)\s*$/i }))
        .first();
      // `Locator.isVisible(options)` is a snapshot check that does NOT
      // poll for visibility — the `timeout` option there only governs
      // locator resolution. `waitFor` is the polling primitive, so use
      // it here so an OIDC-driven UI (e.g. the dashboard, where
      // oidc.js renders the Login link asynchronously after the
      // runtime JS loader fetches the script from the CDN) has time to
      // surface the link before we try to read its href.
      const linkVisible = await loginLink
        .waitFor({ state: "visible", timeout: 20_000 })
        .then(() => true)
        .catch(() => false);
      if (linkVisible) {
        // The role's own UI may intercept clicks asynchronously (e.g.
        // dashboard's oidc.js wraps the Login link in a JS handler that
        // calls keycloak.login() once the adapter has loaded). When the
        // adapter isn't ready yet the click falls through to the native
        // href which already points at openid-connect/auth. Prefer the
        // direct navigation when the href is exposed, and fall back to
        // a real click otherwise; then wait for the OIDC URL to appear
        // either way.
        const href = await loginLink.getAttribute("href").catch(() => null);
        if (href && /openid-connect\/auth/.test(href)) {
          await page.goto(href, { waitUntil: "domcontentloaded" }).catch(() => {});
        } else {
          await loginLink.click().catch(() => {});
          await page
            .waitForURL(/openid-connect\/auth/, { timeout: 15_000 })
            .catch(() => {});
        }
      }
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
      .getByRole("button", { name: /log\s*out|sign\s*out|sign-out|abmelden/i })
      .or(surface.getByRole("link", { name: /log\s*out|sign\s*out|sign-out|abmelden/i }))
      .or(surface.getByRole("menuitem", { name: /log\s*out|sign\s*out|sign-out|abmelden/i }))
      .or(surface.getByRole("button", { name: /(account|profile|user.?menu|^menu$|signed\s*in)/i }))
      .or(surface.getByRole("link", { name: /(account|profile|user.?menu|^menu$|signed\s*in)/i }))
      .or(
        surface.locator(
          "[data-region='user-menu-toggle'], .user-menu-toggle, .usermenu, [aria-label*='user menu' i], [aria-label*='account' i], [data-testid*='user' i], a[href*='logout' i], a[href*='end_session' i], a[href*='end-session' i]",
        ),
      );
  let adminReachedAuthenticated = await adminAuthMarker(page).first().isVisible({ timeout: 15_000 }).catch(() => false);
  if (!adminReachedAuthenticated) {
    for (const frame of page.frames()) {
      if (frame === page.mainFrame()) continue;
      const fUrl = frame.url();
      if (!fUrl || fUrl === "about:blank") continue;
      if (await adminAuthMarker(frame).first().isVisible({ timeout: 1_000 }).catch(() => false)) {
        adminReachedAuthenticated = true;
        break;
      }
    }
  }
  if (!adminReachedAuthenticated) {
    // URL-based fallback for NESTED frames only: see biber.js — the
    // main frame can park on the canonical domain without an
    // authenticated session, so URL alone is not proof of auth.
    for (const frame of page.frames()) {
      if (frame === page.mainFrame()) continue;
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
