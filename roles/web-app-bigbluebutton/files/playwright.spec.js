const { test, expect } = require("@playwright/test");

test.use({ ignoreHTTPSErrors: true });

function decodeDotenvQuotedValue(value) {
  if (typeof value !== "string" || value.length < 2) return value;
  if (!(value.startsWith('"') && value.endsWith('"'))) return value;
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
        originalPolicy: event.originalPolicy
      });
    });
  });
}

async function readCspViolations(page) {
  return page.evaluate(() => window.__cspViolations || []).catch(() => []);
}

const EXPECTED_CSP_DIRECTIVES = [
  "default-src", "connect-src", "frame-ancestors", "frame-src",
  "script-src", "script-src-elem", "script-src-attr",
  "style-src", "style-src-elem", "style-src-attr",
  "font-src", "worker-src", "manifest-src", "media-src", "img-src"
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
  expect(cspHeader, `${label}: Content-Security-Policy response header MUST be present`).toBeTruthy();
  const reportOnly = headers["content-security-policy-report-only"];
  expect(reportOnly, `${label}: Content-Security-Policy-Report-Only MUST NOT be set`).toBeFalsy();
  const parsed = parseCspHeader(cspHeader);
  const missing = EXPECTED_CSP_DIRECTIVES.filter((d) => !parsed[d]);
  expect(missing, `${label}: CSP directives missing from header: ${missing.join(", ")}`).toEqual([]);
  return parsed;
}

async function expectNoCspViolations(page, diagnostics, label) {
  const domViolations = await readCspViolations(page);
  expect(domViolations, `${label}: securitypolicyviolation events: ${JSON.stringify(domViolations)}`).toEqual([]);
  expect(diagnostics.cspRelated, `${label}: CSP-related console/pageerror: ${JSON.stringify(diagnostics.cspRelated)}`).toEqual([]);
}

async function performOidcLogin(frame, username, password) {
  const usernameField = frame.locator("input[name='username'], input#username").first();
  const passwordField = frame.locator("input[name='password'], input#password").first();
  const signInButton = frame
    .locator("input#kc-login, button#kc-login, button[type='submit'], input[type='submit']")
    .first();
  await expect(usernameField).toBeVisible({ timeout: 60_000 });
  await usernameField.fill(username);
  await usernameField.press("Tab");
  await passwordField.fill(password);
  await signInButton.click();
}

const dashboardBaseUrl = normalizeBaseUrl(process.env.APP_BASE_URL || "");
const oidcIssuerUrl = normalizeBaseUrl(process.env.OIDC_ISSUER_URL || "");
const bbbBaseUrl = normalizeBaseUrl(process.env.BBB_BASE_URL || "");
const adminUsername = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const biberUsername = decodeDotenvQuotedValue(process.env.BIBER_USERNAME);
const biberPassword = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD);
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN);

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  expect(dashboardBaseUrl, "APP_BASE_URL must be set (dashboard entry)").toBeTruthy();
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set").toBeTruthy();
  expect(bbbBaseUrl, "BBB_BASE_URL must be set").toBeTruthy();
  expect(adminUsername, "ADMIN_USERNAME must be set").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set").toBeTruthy();
  expect(biberUsername, "BIBER_USERNAME must be set").toBeTruthy();
  expect(biberPassword, "BIBER_PASSWORD must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  await page.context().clearCookies();
  await installCspViolationObserver(page);
});

test("bigbluebutton enforces Content-Security-Policy and exposes canonical domain from applications lookup", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);
  const response = await page.goto(`${bbbBaseUrl}/`);
  expect(response, "Expected BBB landing response").toBeTruthy();
  expect(response.status(), "Expected BBB landing response to be successful").toBeLessThan(400);
  assertCspResponseHeader(response, "bigbluebutton landing");
  const documentUrl = response.url();
  expect(
    documentUrl.includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" to back the BBB URL`
  ).toBe(true);
  await expectNoCspViolations(page, diagnostics, "bigbluebutton landing");
});

// Log out via the universal logout endpoint. Every app's nginx vhost intercepts
// `location = /logout` and proxies it to web-svc-logout, which terminates both
// the Greenlight session and the Keycloak SSO. `waitUntil: 'commit'` avoids
// stalling on any provider-side teardown.
async function bbbLogout(page, bbbBaseUrl) {
  await page
    .goto(`${bbbBaseUrl}/logout`, { waitUntil: "commit" })
    .catch(() => {});
  await page.context().clearCookies();
}

// Greenlight (BBB) auto-submits its SSO form when `?sso=true` is present on the
// SPA root (see greenlight App.jsx#autoSignIn). This is a deterministic SSO
// entry that doesn't depend on React button labels or DOM timing.
async function signInViaBbbOidc(page, username, password, personaLabel) {
  const expectedOidcAuthUrl = `${oidcIssuerUrl}/protocol/openid-connect/auth`;

  await page.goto(`${dashboardBaseUrl}/`);
  await expect(page.locator("body"), `${personaLabel}: dashboard body`).toBeVisible({ timeout: 60_000 });

  await page.goto(`${bbbBaseUrl}/?sso=true`);

  await page.waitForURL((u) => u.toString().includes(expectedOidcAuthUrl), {
    timeout: 120_000
  });

  await performOidcLogin(page, username, password);

  await page.waitForURL((u) => u.toString().startsWith(bbbBaseUrl + "/") && !u.toString().includes("/auth/openid_connect") && !u.toString().includes("?sso=true"), {
    timeout: 120_000
  });

  // Authenticated Greenlight renders a header "Sign Out" control in the nav
  // menu. The unauthenticated landing has "Sign In" / "Sign Up" buttons and
  // never exposes "Sign Out". This is the load-bearing assertion that
  // distinguishes real auth from a short-circuited navigation.
  await page.goto(`${bbbBaseUrl}/rooms`, { waitUntil: "domcontentloaded" });
  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `${personaLabel}: expected /rooms to remain accessible post-login (not to be redirected to / or /signin)`
    })
    .toMatch(new RegExp(`^${bbbBaseUrl.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/rooms(/|\\?|$)`));
}

async function assertLoggedOut(page, bbbBaseUrl, personaLabel) {
  // After logout, /rooms must no longer render the authenticated shell; the
  // unauthenticated Greenlight landing exposes "Sign In" / "Sign Up" or
  // redirects to the sign-in route.
  await page.goto(`${bbbBaseUrl}/rooms`, { waitUntil: "domcontentloaded" }).catch(() => {});
  await expect
    .poll(
      async () => {
        const url = page.url();
        if (/\/(signin|login|ldap_signin)(\/|\?|$)/i.test(url)) return "signin";
        const signInVisible = await page
          .getByRole("link", { name: /sign\s*in|log\s*in|anmelden/i })
          .first()
          .isVisible()
          .catch(() => false);
        if (signInVisible) return "signin";
        const signInButtonVisible = await page
          .getByRole("button", { name: /sign\s*in|log\s*in|anmelden/i })
          .first()
          .isVisible()
          .catch(() => false);
        if (signInButtonVisible) return "signin";
        return "pending";
      },
      {
        timeout: 60_000,
        message: `${personaLabel}: expected bigbluebutton to require a new sign-in after logout`
      }
    )
    .toBe("signin");
}

test("administrator: dashboard to bigbluebutton OIDC login and logout", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);
  await signInViaBbbOidc(page, adminUsername, adminPassword, "administrator");
  await bbbLogout(page, bbbBaseUrl);
  await assertLoggedOut(page, bbbBaseUrl, "administrator");
  await expectNoCspViolations(page, diagnostics, "bigbluebutton administrator OIDC");
});

test("biber: dashboard to bigbluebutton OIDC login and logout", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);
  await signInViaBbbOidc(page, biberUsername, biberPassword, "biber");
  await bbbLogout(page, bbbBaseUrl);
  await assertLoggedOut(page, bbbBaseUrl, "biber");
  await expectNoCspViolations(page, diagnostics, "bigbluebutton biber OIDC");
});
