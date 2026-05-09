/**
 * Logout via the role's own in-app logout control.
 *
 * MUST simulate the user clicking the role's logout button on the
 * currently rendered authenticated surface. Direct URL navigation to
 * any logout endpoint is FORBIDDEN.
 *
 * The universal-logout service (`web-svc-logout`), when attached to a
 * deployment, injects JavaScript that auto-detects every logout control
 * across the apps and rewrites it to redirect through Keycloak's
 * end-session endpoint. The persona helper therefore does NOT branch
 * on whether universal-logout is active: it just clicks the role's own
 * logout button. The injected JS handles the redirect when active, the
 * click clears the local session when not.
 *
 * Resolution order (each step a real click):
 *
 *   1. Click a logout control rendered on the current authenticated
 *      surface (link or button matching `logout` / `sign out` /
 *      `sign-out` / `abmelden`).
 *   2. If the logout control sits behind a user / account menu, open
 *      the menu first, then click the logout control inside it.
 *
 * No further fallback. If neither step finds a control, the test fails
 * — the role's authenticated surface MUST expose an in-app logout.
 */

const { expect } = require("@playwright/test");

const LOGOUT_NAME_RE = /log\s*out|sign\s*out|sign-out|abmelden/i;
const ACCOUNT_MENU_NAME_RE = /^(account|profile|user.?menu|menu)$/i;

async function clickFirstVisible(loc) {
  const visible = await loc.first().isVisible({ timeout: 3_000 }).catch(() => false);
  if (visible) {
    await loc.first().click().catch(() => {});
    return true;
  }
  return false;
}

async function inAppLogout(page) {
  const logoutCandidates = [
    page.getByRole("link", { name: LOGOUT_NAME_RE }),
    page.getByRole("button", { name: LOGOUT_NAME_RE }),
    page.locator("a[href*='logout' i], a[href*='signout' i], a[href*='sign-out' i]"),
  ];

  for (const loc of logoutCandidates) {
    if (await clickFirstVisible(loc)) {
      await page.waitForLoadState("domcontentloaded", { timeout: 30_000 }).catch(() => {});
      return;
    }
  }

  const menuTriggers = [
    page.getByRole("button", { name: ACCOUNT_MENU_NAME_RE }),
    page.locator("[data-region='user-menu-toggle'], .user-menu-toggle, .usermenu, [aria-label*='user menu' i]"),
  ];
  for (const trigger of menuTriggers) {
    if (await clickFirstVisible(trigger)) {
      await page.waitForTimeout(500);
      for (const loc of logoutCandidates) {
        if (await clickFirstVisible(loc)) {
          await page.waitForLoadState("domcontentloaded", { timeout: 30_000 }).catch(() => {});
          return;
        }
      }
    }
  }

  expect.soft(false, "no in-app logout control reachable on the current authenticated surface").toBe(true);
}

module.exports = { inAppLogout };
