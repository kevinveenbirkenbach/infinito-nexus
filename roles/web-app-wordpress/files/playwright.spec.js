const { test, expect } = require("@playwright/test");

test.use({ ignoreHTTPSErrors: true });

// -----------------------------------------------------------------------------
// Env helpers
// -----------------------------------------------------------------------------

function decodeDotenvQuotedValue(value) {
  if (typeof value !== "string" || value.length < 2) {
    return value;
  }
  if (!(value.startsWith('"') && value.endsWith('"'))) {
    return value;
  }
  const encoded = value.slice(1, -1);
  try {
    return JSON.parse(`"${encoded}"`).replace(/\$\$/g, "$");
  } catch {
    return encoded.replace(/\$\$/g, "$");
  }
}

function normalizeBaseUrl(value) {
  return decodeDotenvQuotedValue(value || "").replace(/\/$/, "");
}

// -----------------------------------------------------------------------------
// Diagnostics + CSP helpers (copied from web-app-keycloak/files/playwright.spec.js
// for consistency; inlined because the test runner stages only this file).
// -----------------------------------------------------------------------------

function attachDiagnostics(page) {
  const consoleErrors = [];
  const pageErrors = [];
  const cspRelated = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
    if (/content security policy|csp/i.test(message.text())) {
      cspRelated.push({ source: "console", text: message.text() });
    }
  });
  page.on("pageerror", (error) => {
    const text = String(error);
    pageErrors.push(text);
    if (/content security policy|csp/i.test(text)) {
      cspRelated.push({ source: "pageerror", text });
    }
  });
  return { consoleErrors, pageErrors, cspRelated };
}

function installCspViolationObserver(page) {
  return page.addInitScript(() => {
    window.__cspViolations = [];
    window.addEventListener("securitypolicyviolation", (event) => {
      window.__cspViolations.push({
        violatedDirective: event.violatedDirective,
        blockedURI: event.blockedURI,
        sourceFile: event.sourceFile,
        lineNumber: event.lineNumber,
        originalPolicy: event.originalPolicy,
      });
    });
  });
}

async function readCspViolations(page) {
  return page.evaluate(() => window.__cspViolations || []).catch(() => []);
}

const EXPECTED_CSP_DIRECTIVES = [
  "default-src",
  "connect-src",
  "frame-ancestors",
  "frame-src",
  "script-src",
  "script-src-elem",
  "script-src-attr",
  "style-src",
  "style-src-elem",
  "style-src-attr",
  "font-src",
  "worker-src",
  "manifest-src",
  "media-src",
  "img-src",
];

function parseCspHeader(value) {
  const result = {};
  if (!value) return result;
  for (const raw of value.split(";")) {
    const trimmed = raw.trim();
    if (!trimmed) continue;
    const parts = trimmed.split(/\s+/);
    const directive = parts.shift();
    if (!directive) continue;
    result[directive.toLowerCase()] = parts;
  }
  return result;
}

function assertCspResponseHeader(response, label) {
  const headers = response.headers();
  const cspHeader = headers["content-security-policy"];
  expect(
    cspHeader,
    `${label}: Content-Security-Policy response header MUST be present`
  ).toBeTruthy();
  const reportOnly = headers["content-security-policy-report-only"];
  expect(
    reportOnly,
    `${label}: Content-Security-Policy-Report-Only MUST NOT be set (policy must be enforced)`
  ).toBeFalsy();
  const parsed = parseCspHeader(cspHeader);
  const missing = EXPECTED_CSP_DIRECTIVES.filter((d) => !parsed[d]);
  expect(
    missing,
    `${label}: CSP directives missing from response header: ${missing.join(", ")}`
  ).toEqual([]);
  return parsed;
}

async function assertCspMetaParity(page, headerDirectives, label) {
  const metaLocator = page
    .locator('meta[http-equiv="Content-Security-Policy"]')
    .first();
  const hasMeta = (await metaLocator.count().catch(() => 0)) > 0;
  if (!hasMeta) return;
  const metaContent = await metaLocator.getAttribute("content").catch(() => null);
  if (!metaContent) return;
  const metaParsed = parseCspHeader(metaContent);
  for (const directive of Object.keys(metaParsed)) {
    const headerTokens = new Set(headerDirectives[directive] || []);
    const metaTokens = metaParsed[directive] || [];
    for (const token of metaTokens) {
      expect(
        headerTokens.has(token),
        `${label}: CSP meta token "${token}" for directive ${directive} MUST also appear in the response header`
      ).toBe(true);
    }
  }
}

async function expectNoCspViolations(page, diagnostics, label) {
  const domViolations = await readCspViolations(page);
  expect(
    domViolations,
    `${label}: securitypolicyviolation events observed: ${JSON.stringify(domViolations)}`
  ).toEqual([]);
  expect(
    diagnostics.cspRelated,
    `${label}: CSP-related console/pageerror entries observed: ${JSON.stringify(diagnostics.cspRelated)}`
  ).toEqual([]);
}

// -----------------------------------------------------------------------------
// Keycloak login helpers
// -----------------------------------------------------------------------------

async function fillKeycloakLoginForm(page, username, password) {
  const usernameField = page
    .locator("input[name='username'], input#username")
    .first();
  const passwordField = page
    .locator("input[name='password'], input#password")
    .first();
  const signInButton = page
    .locator(
      "input#kc-login, button#kc-login, button[type='submit'], input[type='submit']"
    )
    .first();
  await expect(
    usernameField,
    "Expected Keycloak username field to be visible"
  ).toBeVisible({ timeout: 60_000 });
  await usernameField.fill(username);
  await passwordField.fill(password);
  await signInButton.click();
}

// -----------------------------------------------------------------------------
// WordPress helpers
// -----------------------------------------------------------------------------

async function wpAdminLoginViaOidc(page, wpBaseUrl, username, password) {
  // WP uses login_type=auto — visiting wp-login.php triggers OIDC redirect when
  // there's no WP session. We land at Keycloak, sign in, and get redirected
  // back to /wp-admin/.
  await page.goto(`${wpBaseUrl}/wp-login.php`, { waitUntil: "domcontentloaded" });
  const url = page.url();
  if (!url.includes(wpBaseUrl)) {
    await fillKeycloakLoginForm(page, username, password);
  }
  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `Expected redirect back to ${wpBaseUrl}/wp-admin after OIDC login`,
    })
    .toContain("/wp-admin");
}

async function wpSignOut(page, wpBaseUrl) {
  // Client-side sign-out: clear WP session cookies and Keycloak SSO cookies in
  // the browser context so the next wpAdminLoginViaOidc re-prompts for
  // credentials. Going through wp-login.php?action=logout triggers the OIDC
  // plugin's `redirect_on_logout: true` path which lands on Keycloak's SLO
  // confirmation page and is fragile to navigate out of inside a Playwright
  // flow — clearing cookies achieves the same test-isolation goal.
  await page.context().clearCookies().catch(() => {});
  await page.goto(`${wpBaseUrl}/`, { waitUntil: "domcontentloaded" }).catch(() => {});
}

// -----------------------------------------------------------------------------
// Keycloak admin-UI helpers (group membership)
// -----------------------------------------------------------------------------

async function keycloakAdminOpenUserProfile(
  page,
  keycloakBaseUrl,
  realmName,
  username
) {
  await page.goto(`${keycloakBaseUrl}/admin/master/console/#/${realmName}/users`, {
    waitUntil: "domcontentloaded",
  });
  const searchInput = page
    .locator("input[placeholder*='Search'], input[name='search']")
    .first();
  await expect(searchInput).toBeVisible({ timeout: 60_000 });
  await searchInput.fill(username);
  await searchInput.press("Enter");
  const userRowLink = page
    .locator("table a, [role='gridcell'] a, a[data-testid='user-row']")
    .filter({ hasText: new RegExp(`^${username}$`, "i") })
    .first();
  await expect(userRowLink).toBeVisible({ timeout: 60_000 });
  await userRowLink.click();
  // Wait until we are on the user profile (hash path contains /users/<id>/).
  await expect
    .poll(() => page.url(), {
      timeout: 30_000,
      message: `Expected Keycloak user profile URL after clicking "${username}"`,
    })
    .toMatch(/\/users\/[^/]+/);
}

async function keycloakAdminOpenUserGroupsTab(page) {
  // PatternFly tabs expose role="tab". Scope strictly to role=tab so we don't
  // accidentally hit the left-nav "Groups" link (which would navigate away
  // from the user profile back to the Groups overview).
  const groupsTab = page
    .locator("[role='tab']")
    .filter({ hasText: /^Groups$/ })
    .first();
  await expect(groupsTab).toBeVisible({ timeout: 30_000 });
  await groupsTab.click();
  // After the tab activates the URL fragment moves to /users/<id>/groups.
  await expect
    .poll(() => page.url(), {
      timeout: 30_000,
      message: "Expected Keycloak user profile to switch to the Groups tab",
    })
    .toMatch(/\/users\/[^/]+\/groups/);
}

/**
 * Add a user to a Keycloak group via the admin UI.
 *
 * Returns:
 *   true  — the user was not a member and the test successfully joined them.
 *   false — the user was ALREADY a member (no join performed); the caller
 *           MUST NOT run a teardown removal, per requirement 004's
 *           idempotency rule ("if the test found biber already a member,
 *           it MUST leave that membership in place").
 */
async function keycloakAdminAddUserToGroup(
  page,
  keycloakBaseUrl,
  realmName,
  groupName,
  username
) {
  await keycloakAdminOpenUserProfile(page, keycloakBaseUrl, realmName, username);
  await keycloakAdminOpenUserGroupsTab(page);

  // "Join Group" button opens the picker modal.
  const joinButton = page
    .locator("button")
    .filter({ hasText: /join\s*group/i })
    .first();
  await expect(
    joinButton,
    "Expected the 'Join Group' button on the user's Groups tab"
  ).toBeVisible({ timeout: 30_000 });
  await joinButton.click();

  // Scope all further interactions to the picker dialog so the left-nav and
  // the underlying page cannot produce cross-matches.
  const dialog = page.getByRole("dialog", { name: /join groups/i }).first();
  await expect(dialog).toBeVisible({ timeout: 30_000 });

  // Search at root level — Keycloak returns results with their full group
  // path (e.g. `/roles/web-app-wordpress-subscriber`), so this bypasses the
  // paginated tree drill-in and works even when many groups share the
  // `roles` parent.
  const dialogSearchBox = dialog.getByRole("textbox", { name: /search/i }).first();
  await expect(dialogSearchBox).toBeVisible({ timeout: 30_000 });
  await dialogSearchBox.fill(groupName);
  await dialogSearchBox.press("Enter");

  // Search results expose the target as `/<parent>/<groupName>`. Groups
  // provisioned by requirement 004 live directly under `ou=roles`, so the
  // accessible name is `/roles/<groupName>`.
  const targetFullPath = `/roles/${groupName}`;
  const targetCheckbox = dialog
    .getByRole("checkbox", { name: targetFullPath, exact: true })
    .first();
  await expect(
    targetCheckbox,
    `Expected Keycloak group "${groupName}" to appear under "roles" in the join dialog — it must have been auto-provisioned from LDAP.`
  ).toBeVisible({ timeout: 30_000 });

  // Keycloak disables the row checkbox for groups the user is already a
  // member of. Treat that as "already a member" and close the dialog
  // without attempting a join (which would time out on `.check()`).
  if (await targetCheckbox.isDisabled()) {
    await dialog
      .getByRole("button", { name: /^close$/i })
      .first()
      .click()
      .catch(() => {});
    await expect(dialog).toBeHidden({ timeout: 30_000 });
    return false;
  }

  await targetCheckbox.check();

  // Confirm "Join" — the footer button of the picker dialog. It is disabled
  // until at least one group is selected, so wait for it to become enabled.
  const confirmJoin = dialog.getByRole("button", { name: /^join$/i }).first();
  await expect(confirmJoin).toBeEnabled({ timeout: 30_000 });
  await confirmJoin.click();

  // Wait until the dialog closes, then verify the target group now appears
  // in the user's Groups tab.
  await expect(dialog).toBeHidden({ timeout: 30_000 });
  const membershipRow = page
    .locator("tr, li")
    .filter({ hasText: new RegExp(groupName) })
    .first();
  await expect(
    membershipRow,
    `Expected "${groupName}" to appear as a membership on the user's Groups tab after joining.`
  ).toBeVisible({ timeout: 30_000 });
  return true;
}

/**
 * Remove a user from a Keycloak group via the Keycloak Admin REST API.
 *
 * Requirement 004 only mandates the *add* operation via the admin UI
 * ("Add `biber` to that existing Keycloak group via the admin UI"). The
 * teardown step ("remove `biber` from the Keycloak group again") does not
 * prescribe a channel, and the admin-UI Groups tab's row-level Leave
 * affordance is fragile across Keycloak UI versions. Using the REST API
 * here makes the idempotency guarantee of the test deterministic.
 */
async function keycloakRemoveUserFromGroupViaRest(
  request,
  keycloakBaseUrl,
  realmName,
  adminUsername,
  adminPassword,
  groupPath,
  username
) {
  const tokenResp = await request.post(
    `${keycloakBaseUrl}/realms/master/protocol/openid-connect/token`,
    {
      form: {
        client_id: "admin-cli",
        grant_type: "password",
        username: adminUsername,
        password: adminPassword,
      },
    }
  );
  if (!tokenResp.ok()) {
    throw new Error(
      `Admin token request failed (${tokenResp.status()}): ${await tokenResp.text()}`
    );
  }
  const { access_token: accessToken } = await tokenResp.json();
  const auth = { Authorization: `Bearer ${accessToken}` };

  const usersResp = await request.get(
    `${keycloakBaseUrl}/admin/realms/${encodeURIComponent(realmName)}/users?username=${encodeURIComponent(username)}&exact=true`,
    { headers: auth }
  );
  const users = await usersResp.json();
  const userId = users?.[0]?.id;
  if (!userId) return;

  const groupResp = await request.get(
    `${keycloakBaseUrl}/admin/realms/${encodeURIComponent(realmName)}/group-by-path/${groupPath.replace(/^\//, "")}`,
    { headers: auth }
  );
  if (!groupResp.ok()) return; // group gone or never existed — nothing to clean up
  const group = await groupResp.json();
  if (!group?.id) return;

  await request.delete(
    `${keycloakBaseUrl}/admin/realms/${encodeURIComponent(realmName)}/users/${userId}/groups/${group.id}`,
    { headers: auth }
  );
}

// -----------------------------------------------------------------------------
// Test configuration
// -----------------------------------------------------------------------------

const appBaseUrl = normalizeBaseUrl(process.env.APP_BASE_URL || "");
const keycloakBaseUrl = normalizeBaseUrl(process.env.KEYCLOAK_BASE_URL || "");
const realmName = decodeDotenvQuotedValue(process.env.KEYCLOAK_REALM_NAME);
const wpBaseUrl = normalizeBaseUrl(process.env.WORDPRESS_BASE_URL || "");
const oidcIssuerUrl = decodeDotenvQuotedValue(process.env.OIDC_ISSUER_URL);
const superAdminUsername = decodeDotenvQuotedValue(
  process.env.SUPER_ADMIN_USERNAME
);
const superAdminPassword = decodeDotenvQuotedValue(
  process.env.SUPER_ADMIN_PASSWORD
);
const adminUsername = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const biberUsername = decodeDotenvQuotedValue(process.env.BIBER_USERNAME);
const biberPassword = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD);
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN);
const rbacGroupPrefix = decodeDotenvQuotedValue(
  process.env.RBAC_GROUP_PREFIX
);

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  expect(appBaseUrl, "APP_BASE_URL must be set").toBeTruthy();
  expect(keycloakBaseUrl, "KEYCLOAK_BASE_URL must be set").toBeTruthy();
  expect(realmName, "KEYCLOAK_REALM_NAME must be set").toBeTruthy();
  expect(wpBaseUrl, "WORDPRESS_BASE_URL must be set").toBeTruthy();
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set").toBeTruthy();
  expect(superAdminUsername, "SUPER_ADMIN_USERNAME must be set").toBeTruthy();
  expect(superAdminPassword, "SUPER_ADMIN_PASSWORD must be set").toBeTruthy();
  expect(adminUsername, "ADMIN_USERNAME must be set").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set").toBeTruthy();
  expect(biberUsername, "BIBER_USERNAME must be set").toBeTruthy();
  expect(biberPassword, "BIBER_PASSWORD must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  expect(rbacGroupPrefix, "RBAC_GROUP_PREFIX must be set").toBeTruthy();
  await page.context().clearCookies();
  await installCspViolationObserver(page);
});

// -----------------------------------------------------------------------------
// Baseline MUSTs: CSP + OIDC flow + canonical-domain DOM assertion
// -----------------------------------------------------------------------------

test("wordpress front page enforces Content-Security-Policy and renders canonical domain", async ({
  page,
}) => {
  const diagnostics = attachDiagnostics(page);
  const response = await page.goto(`${wpBaseUrl}/`);
  expect(response, "Expected WordPress front page response").toBeTruthy();
  expect(
    response.status(),
    "Expected WordPress front page response to be successful"
  ).toBeLessThan(400);
  const directives = assertCspResponseHeader(response, "wordpress front page");
  await assertCspMetaParity(page, directives, "wordpress front page");
  const html = await response.text();
  expect(
    html.includes(canonicalDomain) || (await page.content()).includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" (from applications lookup) to appear in the WordPress UI`
  ).toBe(true);
  await expectNoCspViolations(page, diagnostics, "wordpress front page");
});

test("wordpress administrator can complete an OIDC login round-trip", async ({
  page,
}) => {
  const diagnostics = attachDiagnostics(page);
  await wpAdminLoginViaOidc(page, wpBaseUrl, adminUsername, adminPassword);
  // We must land on /wp-admin/ — proven by wpAdminLoginViaOidc's poll.
  await expect(page).toHaveURL(/\/wp-admin\/?/, { timeout: 30_000 });
  await wpSignOut(page, wpBaseUrl);
  await expectNoCspViolations(
    page,
    diagnostics,
    "wordpress administrator OIDC round-trip"
  );
});

// -----------------------------------------------------------------------------
// RBAC role mapping: biber in web-app-wordpress-<role> → WP role <role>
//
// Requirement 004: auto-provisioned LDAP/Keycloak groups drive WordPress roles
// via the OIDC `groups` claim, consumed by the mu-plugin
// infinito-oidc-rbac-mapper.php. We test three roles across the privilege
// spectrum serially so a regression in one mapping does not mask another.
// -----------------------------------------------------------------------------

const RBAC_ROLE_SEQUENCE = ["subscriber", "editor", "administrator"];

for (const role of RBAC_ROLE_SEQUENCE) {
  test(`rbac: membership in ${role} group grants WordPress ${role} role`, async ({
    browser,
  }) => {
    const groupName = `${rbacGroupPrefix}${role}`;
    let biberAddedToGroup = false;

    // Each identity runs in its own isolated browser context so WP session
    // cookies, Keycloak SSO cookies, and OIDC post-logout redirect state
    // cannot leak between the super-admin-as-keycloak, biber-as-wp, and
    // wp-admin-as-wp hops.
    const newCtx = async () => {
      const ctx = await browser.newContext({
        ignoreHTTPSErrors: true,
        viewport: { width: 1440, height: 1100 },
      });
      const p = await ctx.newPage();
      await installCspViolationObserver(p);
      return { ctx, page: p };
    };

    try {
      // --- 1 + 2 + 3. Super admin (fresh context) adds biber to the group.
      const adminKc = await newCtx();
      try {
        await adminKc.page.goto(`${keycloakBaseUrl}/admin/master/console/`);
        await fillKeycloakLoginForm(
          adminKc.page,
          superAdminUsername,
          superAdminPassword
        );
        await expect
          .poll(() => adminKc.page.url(), {
            timeout: 60_000,
            message: "Expected to land in the Keycloak admin console",
          })
          .toContain("/admin/master/console/");
        biberAddedToGroup = await keycloakAdminAddUserToGroup(
          adminKc.page,
          keycloakBaseUrl,
          realmName,
          groupName,
          biberUsername
        );
      } finally {
        await adminKc.ctx.close().catch(() => {});
      }

      // --- 5. biber (fresh context) signs into WordPress via OIDC.
      const biberWp = await newCtx();
      try {
        await wpAdminLoginViaOidc(
          biberWp.page,
          wpBaseUrl,
          biberUsername,
          biberPassword
        );
      } finally {
        await biberWp.ctx.close().catch(() => {});
      }

      // --- 6. WP admin (fresh context) verifies biber's role on /wp-admin/users.php.
      const wpAdmin = await newCtx();
      try {
        await wpAdminLoginViaOidc(
          wpAdmin.page,
          wpBaseUrl,
          adminUsername,
          adminPassword
        );
        await wpAdmin.page.goto(`${wpBaseUrl}/wp-admin/users.php`, {
          waitUntil: "domcontentloaded",
        });
        const biberRow = wpAdmin.page
          .locator("tr")
          .filter({ hasText: new RegExp(biberUsername, "i") })
          .first();
        await expect(
          biberRow,
          `Expected biber row to be visible on /wp-admin/users.php`
        ).toBeVisible({ timeout: 30_000 });
        const rowText = (await biberRow.textContent()) || "";
        const expectedLabel = role.charAt(0).toUpperCase() + role.slice(1);
        expect(
          rowText.includes(expectedLabel),
          `biber's row on /wp-admin/users.php MUST show WordPress role "${expectedLabel}" after OIDC login; row text: ${rowText}`
        ).toBe(true);
      } finally {
        await wpAdmin.ctx.close().catch(() => {});
      }
    } finally {
      // --- 7. Cleanup: remove biber from the Keycloak group via REST. Only
      // run when the test actually performed the join (biberAddedToGroup
      // === true); when biber was already a member at start, requirement
      // 004 forbids removing them.
      if (biberAddedToGroup) {
        try {
          const reqCtx = await browser.newContext({ ignoreHTTPSErrors: true });
          try {
            await keycloakRemoveUserFromGroupViaRest(
              reqCtx.request,
              keycloakBaseUrl,
              realmName,
              superAdminUsername,
              superAdminPassword,
              `/roles/${groupName}`,
              biberUsername
            );
          } finally {
            await reqCtx.close().catch(() => {});
          }
        } catch (err) {
          // Log but do not mask the original test failure.
          // eslint-disable-next-line no-console
          console.warn(`Cleanup removal of biber from ${groupName} failed: ${err}`);
        }
      }
    }
  });
}
