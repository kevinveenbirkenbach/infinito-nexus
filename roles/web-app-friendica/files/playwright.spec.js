const { test, expect } = require("@playwright/test");

const { decodeDotenvQuotedValue, performKeycloakLoginForm, runGuestFlow } = require("./personas");
const { isServiceEnabled, skipUnlessServiceEnabled } = require("./service-gating");

test.use({
  ignoreHTTPSErrors: true
});

const friendicaBaseUrl = decodeDotenvQuotedValue(process.env.FRIENDICA_BASE_URL);
const canonicalDomain  = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN);
const adminUsername    = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword    = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const biberUsername    = decodeDotenvQuotedValue(process.env.BIBER_USERNAME);
const biberPassword    = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD);

// Variant matrix (see meta/variants.yml):
//   v0  oauth2 + ldap + oidc all enabled — double-login pattern below
//   v1  every dynamic flag disabled      — only guest test runs
//   v2  ldap enabled, oauth2 + oidc off  — direct in-app login (no Keycloak hop)
// All three are selected at runtime by inspecting `OAUTH2_SERVICE_ENABLED`
// and `LDAP_SERVICE_ENABLED` — the spec stays one file across variants.

async function loginViaFriendicaForm(page, username, password) {
  const passwordField = page.locator("input[name='password']").first();
  await passwordField.waitFor({ state: "visible", timeout: 30_000 });

  const usernameField = page.locator("input[name='username']").first();
  const loginForm = page.locator("form").filter({ has: passwordField });
  const signInButton = loginForm
    .locator("button[type='submit'], input[type='submit']")
    .or(loginForm.getByRole("button", { name: /sign\s*in|log\s*in|anmelden|connexion|iniciar|entrar/i }))
    .first();

  await usernameField.fill(username);
  await passwordField.fill(password);
  await Promise.all([
    page.waitForLoadState("domcontentloaded"),
    signInButton.click(),
  ]);
}

// v0 path: oauth2-proxy gates the friendica vhost, so /login first redirects
// through Keycloak — the browser-flow path that ENFORCES 2FA when the realm
// has it configured. After the Keycloak round-trip Friendica still renders
// its OWN login form: there is no header-trusted auto-login addon in stock
// Friendica (Owa.php / OAuth.php only read HTTP_AUTHORIZATION for API auth,
// never for the web session). Fill that second form so `ldapauth`'s
// else-branch (User::getAuthenticationInfo + User::getById against the
// pre-created friendica.user row) starts a Friendica session. See TODO.md
// for the SAML migration that would collapse this back into a single hop.
async function loginViaOauth2ProxyAndFriendica(page, username, password) {
  const baseUrl = friendicaBaseUrl.replace(/\/$/, "");
  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" }).catch(() => {});

  // Step 1: oauth2-proxy intercepted the request — page is now on Keycloak.
  await performKeycloakLoginForm(page, username, password);
  // Wait until the browser hostname is the canonical friendica domain. The
  // naive `url().includes(canonicalDomain)` matches Keycloak's auth URL too
  // (the canonical domain appears in the `redirect_uri` query param), which
  // would let Step 2 run against Keycloak's form instead of Friendica's.
  await expect
    .poll(() => {
      try { return new URL(page.url()).hostname; } catch { return ""; }
    }, {
      timeout: 60_000,
      message: `Expected page hostname to become ${canonicalDomain} after Keycloak login`,
    })
    .toBe(canonicalDomain);

  // Step 2: Friendica's own login form (post-oauth2-proxy).
  await page.waitForLoadState("domcontentloaded", { timeout: 30_000 }).catch(() => {});
  if (await page.locator("input[name='password']").first().isVisible({ timeout: 30_000 }).catch(() => false)) {
    await loginViaFriendicaForm(page, username, password);
  }

  // Verify Friendica's authenticated surface is now rendered. Navigate to
  // an authenticated route explicitly so we don't race a same-page re-render
  // after the POST redirect — the frio / vier themes both expose
  // #topbar-first on /network; `a[href*='/logout']` is the cross-theme
  // fallback for less-canonical themes.
  await page.goto(`${baseUrl}/network`, { waitUntil: "domcontentloaded" }).catch(() => {});
  const profileMenu = page.locator("#topbar-first, #navbar-apps-menu, a[href*='/logout']").first();
  await profileMenu.waitFor({ state: "visible", timeout: 60_000 });
}

// v2 path: no oauth2-proxy gating, friendica's `/login` is directly reachable.
// `ldapauth`'s bind path authenticates against openldap, the pre-created
// administrator row in friendica.user lets the else-branch return a uid →
// hook sets authenticated=1 → session established.
async function loginViaFriendicaDirect(page, username, password) {
  const baseUrl = friendicaBaseUrl.replace(/\/$/, "");
  await page.goto(`${baseUrl}/login`, { waitUntil: "domcontentloaded" });
  await loginViaFriendicaForm(page, username, password);
  await page.goto(`${baseUrl}/network`, { waitUntil: "domcontentloaded" }).catch(() => {});
  const profileMenu = page.locator("#topbar-first, #navbar-apps-menu, a[href*='/logout']").first();
  await profileMenu.waitFor({ state: "visible", timeout: 60_000 });
}

async function friendicaLogout(page) {
  const baseUrl = friendicaBaseUrl.replace(/\/$/, "");
  await page.goto(`${baseUrl}/logout`, { waitUntil: "commit" }).catch(() => {});
}

test("guest: public-landing → auth chain → never authenticated", async ({ page }) => {
  await runGuestFlow(page);
});

// Administrator native login — picks the variant-specific path at runtime.
// Skips entirely when neither oauth2 nor ldap is enabled (v1 has no auth
// providers wired, the role only serves the public landing).
test("friendica: administrator native login and logout", async ({ page }) => {
  skipUnlessServiceEnabled("ldap");

  if (isServiceEnabled("oauth2")) {
    // v0: full double-login via oauth2-proxy + Keycloak round-trip.
    await loginViaOauth2ProxyAndFriendica(page, adminUsername, adminPassword);
  } else {
    // v2: direct /login form, no Keycloak step.
    await loginViaFriendicaDirect(page, adminUsername, adminPassword);
  }

  await friendicaLogout(page);
  await page.goto(`${friendicaBaseUrl.replace(/\/$/, "")}/network`, { waitUntil: "domcontentloaded" }).catch(() => {});
  await expect(page.locator("a[href*='/logout']")).not.toBeAttached({ timeout: 10_000 });
});

// biber + administrator side-by-side: two isolated browser contexts log in
// independently, biber logs out first, admin session must persist. Exercises
// ldapauth's bridge for a non-admin LDAP user AND verifies session isolation
// between contexts. Skips when LDAP is disabled.
test("friendica: biber + administrator side by side in isolated contexts", async ({ browser }) => {
  skipUnlessServiceEnabled("ldap");

  const login = isServiceEnabled("oauth2") ? loginViaOauth2ProxyAndFriendica : loginViaFriendicaDirect;
  const biberContext = await browser.newContext({ ignoreHTTPSErrors: true });
  const adminContext = await browser.newContext({ ignoreHTTPSErrors: true });
  try {
    const biberPage = await biberContext.newPage();
    await login(biberPage, biberUsername, biberPassword);

    const adminPage = await adminContext.newPage();
    await login(adminPage, adminUsername, adminPassword);

    // biber logs out first — admin session must stay alive.
    await friendicaLogout(biberPage);
    await adminPage.goto(`${friendicaBaseUrl.replace(/\/$/, "")}/network`, { waitUntil: "domcontentloaded" });
    await expect(adminPage.locator("a[href*='/logout']").first()).toBeAttached({ timeout: 10_000 });

    await friendicaLogout(adminPage);
  } finally {
    await biberContext.close().catch(() => {});
    await adminContext.close().catch(() => {});
  }
});
