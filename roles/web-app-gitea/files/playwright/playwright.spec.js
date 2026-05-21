const { test, expect } = require("@playwright/test");

const { decodeDotenvQuotedValue, runAdminFlow, runBiberFlow, runGuestFlow } = require("./personas");
test.use({
  ignoreHTTPSErrors: true
});

// `docker --env-file` preserves the quotes emitted by `dotenv_quote`,
// so normalize these values before building URLs or typing credentials.
const gitEaBaseUrl = decodeDotenvQuotedValue(process.env.GITEA_BASE_URL);

test.beforeEach(() => {
  expect(gitEaBaseUrl, "GITEA_BASE_URL must be set in the Playwright env file").toBeTruthy();
});

// Scenario: /healthz/ready on the Gitea domain returns a non-5xx response.
//
// This is the endpoint the Blackbox Exporter probes to determine whether Gitea
// is up. A 200 or 401 means the backend is reachable; 502/503 means the container
// is down. This test verifies the healthz endpoint is wired correctly.
test("healthz/ready endpoint returns non-5xx when gitea is running", async ({ request }) => {
  const healthzUrl = `${gitEaBaseUrl.replace(/\/$/, "")}/healthz/ready`;

  const response = await request.get(healthzUrl);

  expect(
    response.status(),
    `/healthz/ready returned ${response.status()} — ` +
    "502/503 means the Gitea container is down or nginx cannot reach it."
  ).toBeLessThan(500);
});

// Persona scenarios.
// Bodies live in the shared helper roles/test-e2e-playwright/files/personas.js
// so every role's persona flow stays consistent.

test("guest: public-landing → auth chain → never authenticated", async ({ page }) => {
  await runGuestFlow(page);
});

test("biber: app → universal logout", async ({ page }) => {
  await runBiberFlow(page);
});

test("administrator: app → universal logout", async ({ page }) => {
  await runAdminFlow(page, {
    adminInteraction: async (interactivePage) => {
      // web-app-gitea admin-only interaction: open a management surface.
      const link = interactivePage
        .getByRole("link", { name: /^(site administration|admin|user accounts|repositories)$/i })
        .first();
      if (await link.isVisible({ timeout: 10_000 }).catch(() => false)) {
        await link.click().catch(() => {});
        await interactivePage.waitForLoadState("domcontentloaded", { timeout: 30_000 }).catch(() => {});
        await expect(interactivePage.locator("body")).toContainText(
          /site administration|repositories|users|integrations|actions/i,
          { timeout: 30_000 },
        );
      }
    },
  });
});
