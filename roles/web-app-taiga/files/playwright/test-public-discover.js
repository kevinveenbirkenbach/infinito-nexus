const { test, expect } = require("@playwright/test");

exports.register = function (shared) {
  test("taiga public discover keeps the themed surface and hides local login fields when oidc is active", async ({ page }) => {
    shared.skipUnlessServiceEnabled("oidc");

    const taigaUrls = shared.getTaigaUrls();

    await page.goto(taigaUrls.discoverUrl);
    await expect(page.getByRole("heading", { name: /discover projects/i })).toBeVisible({ timeout: 60_000 });
    await shared.expectGradientBackground(
      page.locator("div.master"),
      "Expected the Taiga discover page to use the themed master background",
    );
    await shared.expectGradientBackground(
      page.locator(".discover-header form"),
      "Expected the Taiga discover search form to use the themed surface",
    );
    await shared.expectGradientBackground(
      page.locator(".discover-header input[type='text']"),
      "Expected the Taiga discover search input to use the themed input surface",
    );

    const authState = await shared.reachTopLevelTaigaAuthEntry(
      page,
      taigaUrls,
      60_000,
      "Expected Taiga to expose either the OIDC entry point or the Keycloak login page",
    );

    expect(authState.kind).not.toBe("taiga-local-login-visible");

    if (authState.kind === "taiga-oidc-entry") {
      await expect(authState.locator).toBeVisible({ timeout: 60_000 });
      await expect
        .poll(
          async () => page.locator("input[name='username'], input#username").first().isVisible().catch(() => false),
          {
            timeout: 10_000,
            message: "Expected the local Taiga username field to stay hidden when OIDC is active",
          },
        )
        .toBe(false);
      await expect
        .poll(
          async () => page.locator("input[name='password'], input#password").first().isVisible().catch(() => false),
          {
            timeout: 10_000,
            message: "Expected the local Taiga password field to stay hidden when OIDC is active",
          },
        )
        .toBe(false);
      await expect
        .poll(
          async () => page.getByText(/^or login with$/i).first().isVisible().catch(() => false),
          {
            timeout: 10_000,
            message: "Expected the legacy Taiga OIDC helper text to stay hidden when OIDC is active",
          },
        )
        .toBe(false);
      await expect
        .poll(
          async () => page.getByText(/^forgot it\?$/i).first().isVisible().catch(() => false),
          {
            timeout: 10_000,
            message: "Expected the legacy Taiga password reset helper text to stay hidden when OIDC is active",
          },
        )
        .toBe(false);

      await authState.locator.click();
      await expect
        .poll(
          async () => page.url(),
          {
            timeout: 60_000,
            message: `Expected the Taiga OIDC entry to navigate to Keycloak: ${taigaUrls.expectedOidcAuthUrl}`,
          },
        )
        .toContain(taigaUrls.expectedOidcAuthUrl);
    }

    await expect(page.locator("input[name='username'], input#username").first()).toBeVisible({ timeout: 60_000 });
  });
};
