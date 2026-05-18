// Dedicated console-cleanliness check for the dashboard landing page.
// Scoped narrowly: load /, wait for the dashboard to be ready, then
// assert no unexpected console.error or pageerror events. Two classes
// of expected noise are tolerated (see ``_shared.js``):
//
// - Matomo's cookie-set warnings on test domains
// - Keycloak's silent-check-sso iframe failure (CSP-blocked frame in
//   test envs where the dashboard origin is not a Keycloak
//   frame-ancestor — environment artefact, not a dashboard regression)

const { test, expect } = require("@playwright/test");

exports.register = function (shared) {
  test("dashboard landing renders without unexpected console or page errors", async ({ page }) => {
    const diagnostics = shared.attachDiagnostics(page);
    const documentResponse = await page.goto("/");
    expect(documentResponse.status()).toBeLessThan(400);

    await shared.waitForDashboardReady(page);

    shared.expectNoUnexpectedDiagnostics(diagnostics, {
      ignoreMatomoConsoleNoise: true,
      ignoreOidcSilentCheckNoise: true,
    });
  });
};
