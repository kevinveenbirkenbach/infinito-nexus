/**
 * Drive a Keycloak OIDC login form with the given credentials.
 *
 * The function expects the page to already sit on a Keycloak
 * authorization endpoint (`.../openid-connect/auth?...`). It fills the
 * username + password fields, clicks the sign-in button, and waits
 * until the URL has left Keycloak and is back on the role's canonical
 * domain (the OAuth2-Proxy / app callback).
 */

const { expect } = require("@playwright/test");

async function performKeycloakLogin(page, username, password, canonicalDomain) {
  const usernameField = page
    .getByRole("textbox", { name: /username|email/i })
    .or(page.locator("input[name='username'], input#username"))
    .first();
  const passwordField = page
    .getByRole("textbox", { name: /^password$/i })
    .or(page.locator("input[name='password'], input#password"))
    .first();
  const signInButton = page
    .getByRole("button", { name: /sign in|login|log in/i })
    .or(page.locator("input#kc-login, button#kc-login, button[type='submit'], input[type='submit']"))
    .first();

  await usernameField.waitFor({ state: "visible", timeout: 60_000 });
  await usernameField.fill(username);
  await usernameField.press("Tab").catch(() => {});
  await passwordField.fill(password);
  await signInButton.click();

  await expect
    .poll(() => page.url(), {
      timeout: 60_000,
      message: `Expected redirect back to ${canonicalDomain} after Keycloak login`,
    })
    .toContain(canonicalDomain);
}

/**
 * Drive a Keycloak OIDC login form with credentials that are expected
 * to be REJECTED (insufficient privileges, forbidden role, denied app).
 *
 * Used for the biber-vs-prometheus / biber-vs-matomo deny-login
 * assertions: biber's OIDC account exists in Keycloak but does NOT
 * carry the realm role / client mapping required to reach the admin
 * surface, so the login round-trip MUST end on either:
 *   - a Keycloak error page (e.g. "Access denied") on the IdP, or
 *   - the same authorization endpoint with an error indicator, or
 *   - a 401/403 on the relying party after the callback.
 *
 * The function returns the resulting URL so callers can assert
 * additional details if needed.
 */
async function performKeycloakLoginExpectingDenial(page, username, password, canonicalDomain) {
  const usernameField = page
    .getByRole("textbox", { name: /username|email/i })
    .or(page.locator("input[name='username'], input#username"))
    .first();
  const passwordField = page
    .getByRole("textbox", { name: /^password$/i })
    .or(page.locator("input[name='password'], input#password"))
    .first();
  const signInButton = page
    .getByRole("button", { name: /sign in|login|log in/i })
    .or(page.locator("input#kc-login, button#kc-login, button[type='submit'], input[type='submit']"))
    .first();

  await usernameField.waitFor({ state: "visible", timeout: 60_000 });
  await usernameField.fill(username);
  await usernameField.press("Tab").catch(() => {});
  await passwordField.fill(password);
  await signInButton.click();

  await page.waitForLoadState("domcontentloaded", { timeout: 60_000 }).catch(() => {});

  const finalUrl = page.url();
  const denied =
    /access[\s_-]?denied|forbidden|not[\s_-]?authori[sz]ed|unauthori[sz]ed/i.test(
      await page.content().catch(() => ""),
    ) ||
    /openid-connect\/auth/.test(finalUrl) ||
    !finalUrl.includes(canonicalDomain);

  expect(
    denied,
    `Expected ${username} to be DENIED at ${canonicalDomain} after Keycloak login (got URL ${finalUrl})`,
  ).toBe(true);

  return finalUrl;
}

module.exports = { performKeycloakLogin, performKeycloakLoginExpectingDenial };
