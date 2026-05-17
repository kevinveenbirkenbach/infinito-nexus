const { test, expect } = require("@playwright/test");

exports.register = function (shared) {
  test("admin: nextcloud oidc login and logout", async ({ page }) => {
    test.skip(
      !shared.env.nextcloudOidcEnabled,
      "Admin OIDC login is only exercised when services.oidc.enabled is true — the native form covers the OIDC-off variant.",
    );

    await shared.loginToStandaloneNextcloud(page);

    const shellState = await shared.waitForVisibleCandidate(
      page,
      shared.getNextcloudShellCandidates(page),
      60_000,
      "Timed out waiting for a signed-in Nextcloud shell after the Keycloak login redirect",
    );
    await expect(shellState.locator).toBeVisible();

    // First login can show one or more stacked onboarding dialogs that block clicks.
    await shared.dismissBlockingNextcloudModals(page, page);

    // Reuse the authenticated context to verify the Talk admin chrome
    // (HPB / STUN / TURN values plus the spreed reachability buttons).
    // No-op when NEXTCLOUD_TALK_SETTINGS_CHECK_ENABLED is false.
    await shared.verifyNextcloudTalkAdminSettings(page.context());

    await shared.logoutStandaloneNextcloud(page);
  });
};
