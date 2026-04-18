const { test, expect } = require("@playwright/test");

test.use({
  ignoreHTTPSErrors: true
});

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

// `docker --env-file` preserves the quotes emitted by `dotenv_quote`,
// so normalize these values before building URLs or typing credentials.
const oidcIssuerUrl     = decodeDotenvQuotedValue(process.env.OIDC_ISSUER_URL);
const prometheusBaseUrl = decodeDotenvQuotedValue(process.env.PROMETHEUS_BASE_URL);
const gitEaBaseUrl      = decodeDotenvQuotedValue(process.env.GITEA_BASE_URL);
const adminUsername     = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword     = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);

// Perform SSO login via Keycloak.
async function performOidcLogin(locator, username, password) {
  const usernameField = locator.getByRole("textbox", { name: /username|email/i });
  const passwordField = locator.getByRole("textbox", { name: "Password" });
  const signInButton  = locator.getByRole("button", { name: /sign in/i });

  await usernameField.waitFor({ state: "visible", timeout: 60_000 });
  await usernameField.fill(username);
  await usernameField.press("Tab");
  await passwordField.fill(password);
  await signInButton.click();
}

test.beforeEach(() => {
  expect(prometheusBaseUrl, "PROMETHEUS_BASE_URL must be set in the Playwright env file").toBeTruthy();
  expect(gitEaBaseUrl,      "GITEA_BASE_URL must be set in the Playwright env file").toBeTruthy();
});

// Scenario I: /metricz on the prometheus domain exposes metrics for Gitea.
//
// Gitea declares prometheus as a shared service dependency. When prometheus is
// deployed alongside Gitea, lua-resty-prometheus records per-request metrics for
// the Gitea vhost and exposes them via the single /metricz scrape endpoint on the
// prometheus domain. This test verifies the end-to-end contract:
//   1. /metricz returns HTTP 200 with prometheus text-format content.
//   2. The response contains at least one metric line labeled app="web-app-gitea",
//      confirming that Gitea's vhost is tracked by the shared metrics dict.
//
// /metricz is intentionally unauthenticated — prometheus must scrape it without
// bearer tokens or OAuth2. If this test returns 401/403, the nginx ACL whitelist
// for /metricz is misconfigured.
test("metricz endpoint exposes gitea metrics when prometheus is loaded as dependency", async ({ request }) => {
  const metriczUrl = `${prometheusBaseUrl.replace(/\/$/, "")}/metricz`;

  const response = await request.get(metriczUrl);

  if (response.status() === 404) {
    test.skip(true, "/metricz returned 404 — prometheus nginx vhost not deployed in this CI run (deploy web-app-prometheus explicitly to enable this test)");
    return;
  }

  expect(
    response.status(),
    `/metricz must return 200 — got ${response.status()}. ` +
    "If 401/403, the nginx ACL whitelist for /metricz is misconfigured."
  ).toBe(200);

  const body = await response.text();

  // Prometheus text format always begins comment lines with '#'.
  expect(body, "/metricz response must be prometheus text format (lines starting with #)").toMatch(/^#/m);

  // At least one metric must carry the Gitea app label, confirming the vhost
  // is tracked in the shared lua-resty-prometheus memory dict.
  expect(
    body,
    `/metricz must contain metrics labeled app="web-app-gitea" — ` +
    "if missing, the Gitea vhost is not registered in lua-resty-prometheus."
  ).toContain('app="web-app-gitea"');
});

// Scenario II: Prometheus scrapes Gitea native metrics — the gitea job target is up.
//
// When native_metrics.enabled=true in the Gitea inventory, Gitea exposes /metrics on
// its main HTTP port. Prometheus scrapes it via an internal port binding
// (host.docker.internal:PORT) rather than going through nginx/OAuth2.
// This test authenticates against Prometheus via SSO and queries the Prometheus HTTP
// API to confirm the gitea job has at least one UP target (value=1).
//
// The test is skipped when:
//   - PROMETHEUS_BASE_URL or OIDC_ISSUER_URL are unset (prometheus not deployed)
//   - The query returns no results (native_metrics.enabled=false in this deployment)
test("prometheus scrapes gitea native metrics — job target is up", async ({ browser, request }) => {
  if (!prometheusBaseUrl || !oidcIssuerUrl) {
    test.skip(true, "PROMETHEUS_BASE_URL or OIDC_ISSUER_URL not set — prometheus not deployed in this CI run");
    return;
  }

  const metriczPreflight = await request.get(`${prometheusBaseUrl.replace(/\/$/, "")}/metricz`);
  if (metriczPreflight.status() === 404) {
    test.skip(true, "Prometheus nginx vhost not deployed in this CI run (deploy web-app-prometheus explicitly to enable this test)");
    return;
  }

  const ctx = await browser.newContext({ ignoreHTTPSErrors: true });

  try {
    const page = await ctx.newPage();

    // Navigate to prometheus — triggers SSO redirect to Keycloak.
    await page.goto(prometheusBaseUrl);

    await expect
      .poll(() => page.url(), {
        timeout: 30_000,
        message: `Expected redirect to Keycloak OIDC issuer: ${oidcIssuerUrl}`
      })
      .toContain(oidcIssuerUrl);

    await performOidcLogin(page, adminUsername, adminPassword);

    await expect
      .poll(() => page.url(), {
        timeout: 30_000,
        message: `Expected redirect back to Prometheus: ${prometheusBaseUrl}`
      })
      .toContain(prometheusBaseUrl.replace(/\/$/, ""));

    // Query the Prometheus HTTP API for the gitea job's up metric.
    const queryUrl = `${prometheusBaseUrl.replace(/\/$/, "")}/api/v1/query?query=up%7Bjob%3D%22gitea%22%7D`;
    const response = await ctx.request.get(queryUrl);

    expect(
      response.ok(),
      `Prometheus API returned ${response.status()} — expected 200.`
    ).toBeTruthy();

    const data = await response.json();

    expect(
      data.status,
      `Prometheus API response status must be "success", got: ${data.status}`
    ).toBe("success");

    const results = data.data.result;

    if (results.length === 0) {
      test.skip(true, "No gitea job in Prometheus — native_metrics.enabled=false in this deployment");
      return;
    }

    const value = parseFloat(results[0].value[1]);

    expect(
      value,
      `Prometheus up{job="gitea"} must be 1 (target UP) — got ${value}. ` +
      "If 0, the Gitea container is down or the internal port binding is broken."
    ).toBe(1);

  } finally {
    await ctx.close().catch(() => {});
  }
});

// Scenario III: /healthz/ready on the Gitea domain returns a non-5xx response.
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
