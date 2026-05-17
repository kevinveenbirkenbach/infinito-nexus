const { test } = require("@playwright/test");

exports.register = function (shared) {
  test("nextcloud talk admin settings", async ({ browser }) => {
    test.skip(!shared.env.nextcloudTalkSettingsCheckEnabled, "Talk admin checks are disabled in the current Playwright env");

    const browserContext = await browser.newContext({
      ignoreHTTPSErrors: true
    });

    try {
      await shared.verifyNextcloudTalkAdminSettings(browserContext);
    } finally {
      await browserContext.close().catch(() => {});
    }
  });
};
