const { test, expect, request } = require("@playwright/test");

const { skipUnlessServiceEnabled, isServiceEnabled } = require("./service-gating");
const { decodeDotenvQuotedValue, runAdminFlow, runBiberFlow, runGuestFlow } = require("./personas");
test.use({ ignoreHTTPSErrors: true });

const dashboardBaseUrl   = decodeDotenvQuotedValue(process.env.DASHBOARD_BASE_URL   || "").replace(/\/$/, "");
const appBaseUrl         = decodeDotenvQuotedValue(process.env.APP_BASE_URL         || "").replace(/\/$/, "");
const canonicalDomain    = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN     || "");
const oidcIssuerUrl      = decodeDotenvQuotedValue(process.env.OIDC_ISSUER_URL      || "").replace(/\/$/, "");
const logoutUrl          = decodeDotenvQuotedValue(process.env.LOGOUT_URL           || "").replace(/\/$/, "");
const kcBaseUrl          = decodeDotenvQuotedValue(process.env.KEYCLOAK_BASE_URL    || "").replace(/\/$/, "");
const kcRealm            = decodeDotenvQuotedValue(process.env.KEYCLOAK_REALM       || "");
const kcAdminUser        = decodeDotenvQuotedValue(process.env.KEYCLOAK_ADMIN_USERNAME || "");
const kcAdminPw          = decodeDotenvQuotedValue(process.env.KEYCLOAK_ADMIN_PASSWORD || "");
const kixUserGroupPath   = decodeDotenvQuotedValue(process.env.KIX_USER_GROUP_PATH  || "");
const adminUsername      = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME       || "");
const adminPassword      = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD       || "");
const biberUsername      = decodeDotenvQuotedValue(process.env.BIBER_USERNAME       || "");
const biberPassword      = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD       || "");

async function performKeycloakLogin(page, username, password) {
  const usernameField = page.getByRole("textbox", { name: /username|email/i });
  const passwordField = page.getByRole("textbox", { name: "Password" });
  const signInButton  = page.getByRole("button", { name: /sign in/i });

  await usernameField.waitFor({ state: "visible", timeout: 60_000 });
  await usernameField.fill(username);
  await usernameField.press("Tab");
  await passwordField.fill(password);
  await signInButton.click();
}

async function performKixLogin(page, username, password) {
  const usernameInput = page.locator('input[type="text"], input[type="email"], input[name="UserLogin"], input[name="username"]').first();
  const passwordInput = page.locator('input[type="password"]').first();
  const submitButton  = page.locator('button[type="submit"], input[type="submit"], button:has-text("Login")').first();

  await usernameInput.waitFor({ state: "visible", timeout: 30_000 });
  await usernameInput.fill(username);
  await passwordInput.fill(password);
  await submitButton.click();
}

async function ensureUserInGroup(username, groupPath) {
  const api = await request.newContext({ ignoreHTTPSErrors: true });

  const tokenResp = await api.post(
    `${kcBaseUrl}/realms/master/protocol/openid-connect/token`,
    {
      form: {
        client_id: "admin-cli",
        username:  kcAdminUser,
        password:  kcAdminPw,
        grant_type: "password",
      },
    },
  );
  if (!tokenResp.ok()) {
    throw new Error(`Keycloak admin token failed: ${tokenResp.status()} ${await tokenResp.text()}`);
  }
  const accessToken = (await tokenResp.json()).access_token;
  const auth = { Authorization: `Bearer ${accessToken}` };

  const usersResp = await api.get(
    `${kcBaseUrl}/admin/realms/${kcRealm}/users?username=${encodeURIComponent(username)}&exact=true`,
    { headers: auth },
  );
  if (!usersResp.ok()) {
    throw new Error(`Keycloak user lookup failed: ${usersResp.status()} ${await usersResp.text()}`);
  }
  const users = await usersResp.json();
  if (!users.length) {
    throw new Error(`Keycloak user '${username}' not found in realm ${kcRealm}`);
  }
  const userId = users[0].id;

  const groupResp = await api.get(
    `${kcBaseUrl}/admin/realms/${kcRealm}/group-by-path${groupPath}`,
    { headers: auth },
  );
  if (!groupResp.ok()) {
    throw new Error(`Keycloak group lookup failed for ${groupPath}: ${groupResp.status()} ${await groupResp.text()}`);
  }
  const group = await groupResp.json();
  const groupId = group.id;

  const putResp = await api.put(
    `${kcBaseUrl}/admin/realms/${kcRealm}/users/${userId}/groups/${groupId}`,
    { headers: auth },
  );
  if (![200, 204].includes(putResp.status())) {
    throw new Error(`Keycloak group assignment failed: ${putResp.status()} ${await putResp.text()}`);
  }

  await api.dispose();
}

test.beforeEach(async ({ page }) => {
  expect(dashboardBaseUrl, "DASHBOARD_BASE_URL must be set").toBeTruthy();
  expect(appBaseUrl,       "APP_BASE_URL must be set").toBeTruthy();
  expect(canonicalDomain,  "CANONICAL_DOMAIN must be set").toBeTruthy();
  expect(oidcIssuerUrl,    "OIDC_ISSUER_URL must be set").toBeTruthy();
  expect(logoutUrl,        "LOGOUT_URL must be set").toBeTruthy();
  expect(kcBaseUrl,        "KEYCLOAK_BASE_URL must be set").toBeTruthy();
  expect(kcRealm,          "KEYCLOAK_REALM must be set").toBeTruthy();
  expect(kixUserGroupPath, "KIX_USER_GROUP_PATH must be set").toBeTruthy();
  expect(adminUsername,    "ADMIN_USERNAME must be set").toBeTruthy();
  expect(adminPassword,    "ADMIN_PASSWORD must be set").toBeTruthy();
  expect(biberUsername,    "BIBER_USERNAME must be set").toBeTruthy();
  expect(biberPassword,    "BIBER_PASSWORD must be set").toBeTruthy();
  await page.context().clearCookies();
});

test("kix root emits TLS+HSTS", async ({ page }) => {
  const response = await page.goto(`${appBaseUrl}/`);
  expect(response, "Expected a response from the KIX root").toBeTruthy();
  expect(response.status(), "Expected KIX root status < 500").toBeLessThan(500);
  const headers = response.headers();
  expect(headers["strict-transport-security"], "kix must emit HSTS").toBeTruthy();
});

async function runKixLoginLogoutFlow(page, username, password) {
  const expectedAuthUrl = `${oidcIssuerUrl}/protocol/openid-connect/auth`;

  await page.goto(`${dashboardBaseUrl}/`, { waitUntil: "domcontentloaded" });
  const kixCard = page.locator(`a[href*="${canonicalDomain}"]`).first();
  await expect(kixCard, "KIX dashboard link must be present in the DOM").toHaveCount(1, { timeout: 30_000 });
  const kixHref = await kixCard.getAttribute("href");
  expect(kixHref, "KIX dashboard link must point at the canonical KIX URL").toContain(canonicalDomain);
  await page.goto(kixHref);

  await expect
    .poll(() => page.url(), {
      timeout: 30_000,
      message: `Expected redirect to Keycloak OIDC auth: ${expectedAuthUrl}`,
    })
    .toContain(expectedAuthUrl);
  await performKeycloakLogin(page, username, password);

  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `Expected redirect back to canonical KIX URL on ${canonicalDomain}`,
    })
    .toContain(canonicalDomain);

  await page.waitForLoadState("domcontentloaded");
  await performKixLogin(page, username, password);

  await expect
    .poll(() => page.url(), {
      timeout: 30_000,
      message: `Expected SPA to leave /auth after successful LDAP login as ${username}`,
    })
    .not.toContain("/auth");

  await page.goto(logoutUrl, { waitUntil: "commit" }).catch(() => {});

  await page.context().clearCookies();
  await page.goto(`${appBaseUrl}/`, { waitUntil: "domcontentloaded" });
  await expect
    .poll(() => page.url(), {
      timeout: 30_000,
      message: `Expected post-logout request to be re-gated to ${expectedAuthUrl}`,
    })
    .toContain(expectedAuthUrl);
}

test("administrator: full login flow (dashboard → KIX card → OAuth2-proxy → Keycloak → KIX-LDAP login → KIX UI → universal logout)", async ({ page }) => {
  await runKixLoginLogoutFlow(page, adminUsername, adminPassword);
});

test("biber (granted web-app-kix-user via Keycloak): full login flow (dashboard → KIX card → OAuth2-proxy → Keycloak → KIX-LDAP login → KIX UI → universal logout)", async ({ page }) => {
  await ensureUserInGroup(biberUsername, kixUserGroupPath);
  await runKixLoginLogoutFlow(page, biberUsername, biberPassword);
});

// Persona scenarios (req 019 Rule 3).
// Bodies live in the shared helper roles/test-e2e-playwright/files/personas.js
// so every role's persona flow stays consistent.

test("guest: public-landing → auth chain → never authenticated", async ({ page }) => {
  await runGuestFlow(page);
});

test("biber: dashboard → app → universal logout", async ({ page }) => {
  await runBiberFlow(page);
});
