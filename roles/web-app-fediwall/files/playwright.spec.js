const { test, expect } = require("@playwright/test");
const { skipUnlessServiceEnabled } = require("./service-gating");

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

const appBaseUrl = normalizeBaseUrl(process.env.APP_BASE_URL || "");
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN || "");
const defaultSlug = decodeDotenvQuotedValue(process.env.FEDIWALL_DEFAULT_SLUG || "");
const wallSlugs = JSON.parse(decodeDotenvQuotedValue(process.env.FEDIWALL_WALL_SLUGS || "[]"));
const mastodonBaseUrl = normalizeBaseUrl(process.env.MASTODON_BASE_URL || "");
const friendicaBaseUrl = normalizeBaseUrl(process.env.FRIENDICA_BASE_URL || "");
const biberUsername = decodeDotenvQuotedValue(process.env.BIBER_USERNAME || "");
const biberPassword = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD || "");

test.beforeEach(async ({ page }) => {
  expect(appBaseUrl, "APP_BASE_URL must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  expect(defaultSlug, "FEDIWALL_DEFAULT_SLUG must be set").toBeTruthy();
  await page.context().clearCookies();
});

// -----------------------------------------------------------------------------
// Baseline scenarios — MUST pass even when every shared service is disabled.
// -----------------------------------------------------------------------------

test("fediwall root is served under canonical domain with TLS", async ({ page }) => {
  const response = await page.goto(`${appBaseUrl}/`);
  expect(response, "Expected fediwall root response").toBeTruthy();
  expect(response.status(), "Expected fediwall root status < 400").toBeLessThan(400);
  expect(
    response.url().includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" to back the fediwall URL`
  ).toBe(true);
  const headers = response.headers();
  expect(headers["strict-transport-security"], "fediwall must emit HSTS").toBeTruthy();
});

test("fediwall root resolves to the configured default slug", async ({ page }) => {
  await page.goto(`${appBaseUrl}/`);
  if (wallSlugs.length <= 1) {
    // Single-wall deploy: root MUST redirect to the only wall's path.
    await expect(page).toHaveURL(new RegExp(`/${defaultSlug}/?$`));
  } else {
    // Multi-wall deploy: root MUST present an entry for every slug.
    for (const slug of wallSlugs) {
      await expect(page.locator(`a[href="./${slug}/"]`)).toBeVisible();
    }
  }
});

test("fediwall default slug returns HTML content", async ({ request }) => {
  const response = await request.get(`${appBaseUrl}/${defaultSlug}/`);
  expect(response.status(), "Expected default-slug status < 400").toBeLessThan(400);
  const contentType = response.headers()["content-type"] || "";
  expect(
    contentType.includes("text/html"),
    `Expected HTML content-type, got "${contentType}"`
  ).toBe(true);
});

test("fediwall default slug ships its baked-in wall-config.json", async ({ request }) => {
  const response = await request.get(`${appBaseUrl}/${defaultSlug}/wall-config.json`);
  expect(
    response.status(),
    "Expected default-slug wall-config.json to be reachable for client-side bootstrap"
  ).toBeLessThan(400);
  const body = await response.json();
  expect(
    Array.isArray(body.servers),
    "wall-config.json MUST expose a servers array so Fediwall can bootstrap"
  ).toBe(true);
});

test("fediwall default slug mounts its Vue SPA into the document body", async ({ page }) => {
  await page.goto(`${appBaseUrl}/${defaultSlug}/`);
  await expect(page.locator("#app")).toBeAttached();
});

// -----------------------------------------------------------------------------
// Cross-Fediverse scenario — runs whenever Mastodon AND Friendica are
// deployed alongside fediwall. The test is fully data-driven against
// each wall's `wall-config.json` `servers` list:
//
//   - biber posts a unique status to BOTH Mastodon and Friendica via
//     the same SSO/ldapauth UI flow a human would use (LDAP is the
//     single source of truth for biber's credentials; the local
//     accounts on Mastodon/Friendica come into existence lazily on
//     first SSO login, exactly as in production — no API auth, no
//     password duplication, no manual user provisioning).
//
//   - For every deployed wall, the test reads `wall-config.json`
//     and asserts: a sibling's post is visible iff that sibling's
//     domain is listed in `servers`; otherwise it MUST NOT appear.
//
// This single test covers both variants automatically:
//   variant 0 — one wall polling all active siblings (both posts visible)
//   variant 1 — two walls; one polls both siblings, the other only
//               Mastodon (friendica post must be absent there).
// -----------------------------------------------------------------------------

// Keycloak login form — same selector set the keycloak role's playwright spec
// uses (input[name='username'] / input[name='password'] / input#kc-login).
async function fillKeycloakLoginIfPresent(page, username, password) {
  const usernameField = page.locator("input[name='username'], input#username").first();
  if (!(await usernameField.isVisible({ timeout: 30_000 }).catch(() => false))) {
    return false;
  }
  await usernameField.fill(username);
  await page.locator("input[name='password'], input#password").first().fill(password);
  await page
    .locator("input#kc-login, button#kc-login, button[type='submit'], input[type='submit']")
    .first()
    .click();
  return true;
}

// Drive Mastodon's OIDC login flow as biber. Lands on the Mastodon home
// timeline once Keycloak redirects back. First-time login auto-creates
// biber's local Mastodon account through the openid_connect plugin.
//
// Mastodon renders the OIDC sign-in button as a Rails-UJS pseudo-form:
//
//   <a class="btn button-openid_connect" data-method="post"
//      href="/auth/auth/openid_connect">…</a>
//
// A plain Playwright click() submits a regular GET, which Mastodon
// answers with HTTP 404 ("redirect endpoint expects POST"). We bypass
// Rails-UJS by building and submitting an actual <form method="post">
// in the page, with the CSRF token Mastodon embedded in <meta>.
async function loginToMastodonViaOidc(page, baseUrl) {
  await page.goto(`${baseUrl}/auth/sign_in`);
  const oidcLink = page.locator("a[href*='/auth/auth/openid_connect'], a[href*='/auth/openid_connect']").first();
  await expect(oidcLink, "Expected Mastodon OIDC sign-in link").toBeVisible({ timeout: 30_000 });

  await Promise.all([
    page.waitForNavigation({ waitUntil: "domcontentloaded" }),
    page.evaluate(() => {
      const a = document.querySelector(
        "a[href*='/auth/auth/openid_connect'], a[href*='/auth/openid_connect']"
      );
      if (!a) throw new Error("OIDC sign-in anchor disappeared before submit");
      const csrfMeta = document.querySelector("meta[name='csrf-token']");
      const csrfParamMeta = document.querySelector("meta[name='csrf-param']");
      const form = document.createElement("form");
      form.method = "POST";
      form.action = a.getAttribute("href");
      if (csrfMeta && csrfParamMeta) {
        const tokenInput = document.createElement("input");
        tokenInput.type = "hidden";
        tokenInput.name = csrfParamMeta.getAttribute("content");
        tokenInput.value = csrfMeta.getAttribute("content");
        form.appendChild(tokenInput);
      }
      document.body.appendChild(form);
      form.submit();
    }),
  ]);

  const filled = await fillKeycloakLoginIfPresent(page, biberUsername, biberPassword);
  expect(filled, "Expected Keycloak login form to render after OIDC redirect").toBe(true);

  // First-time OIDC login on Mastodon 4.x renders a "Profile setup"
  // wizard (display name + bio + discoverability) modally over the
  // home column. Playwright's compose-textarea click is intercepted
  // by the modal layer, so dismiss the wizard via "Save and continue"
  // when it appears. The wizard does not appear on subsequent logins.
  const saveAndContinue = page
    .locator("button[type='submit'], button")
    .filter({ hasText: /save and continue/i })
    .first();
  if (await saveAndContinue.isVisible({ timeout: 10_000 }).catch(() => false)) {
    await saveAndContinue.click();
  }

  // The compose textarea sits at the top of the home column. Mastodon
  // 4.x uses the placeholder "What's on your mind?" — match on the
  // distinctive substring "mind" to avoid quoting the apostrophe.
  await expect(
    page
      .locator(
        "textarea[name='status'], textarea[placeholder*='mind'], textarea#status_text"
      )
      .first(),
    "Expected Mastodon compose textarea after OIDC sign-in"
  ).toBeVisible({ timeout: 60_000 });
}

async function postOnMastodonViaUi(page, baseUrl, statusText) {
  await loginToMastodonViaOidc(page, baseUrl);
  const compose = page
    .locator(
      "textarea[name='status'], textarea[placeholder*='mind'], textarea#status_text"
    )
    .first();
  await compose.fill(statusText);
  // The "Publish" / "Post" / "Toot" button label changes between Mastodon
  // releases. Match the submit-role button inside the compose form.
  const publish = page.locator("button[type='submit']").filter({ hasText: /publish|post|toot/i }).first();
  await publish.click();
  // Mastodon clears the textarea after a successful post.
  await expect(compose, "Expected Mastodon compose textarea to clear after publish").toHaveValue(
    "",
    { timeout: 30_000 }
  );
}

// Drive Friendica's form login (ldapauth-mediated) as biber, then post
// via the dedicated `/compose` page. The frio theme inlines a hidden
// `jot` form on /network that depends on JS state to enable the submit
// button — `/compose` renders the same form as a standalone page with
// the textarea + submit button always visible, so it is the most stable
// target for an end-to-end UI flow.
async function postOnFriendicaViaUi(page, baseUrl, statusText) {
  await page.goto(`${baseUrl}/login`, { waitUntil: "domcontentloaded" });
  await page.locator("input[name='username']").waitFor({ state: "visible", timeout: 60_000 });
  await page.locator("input[name='username']").fill(biberUsername);
  await page.locator("input[name='password']").fill(biberPassword);
  await Promise.all([
    page.waitForLoadState("domcontentloaded"),
    page.getByRole("button", { name: "Sign in", exact: true }).click(),
  ]);

  await page.goto(`${baseUrl}/compose`, { waitUntil: "domcontentloaded" });
  const compose = page.locator("textarea[name='body']").first();
  await expect(
    compose,
    "Expected Friendica /compose textarea after ldapauth sign-in"
  ).toBeVisible({ timeout: 60_000 });
  await compose.fill(statusText);
  // /compose renders a stand-alone form with a visible "Submit" button
  // (`button[name='submit']` inside `#comment-edit-form-0`). Click it
  // directly — no jothidden / requestSubmit gymnastics needed.
  await page.locator("button[name='submit'][type='submit']").first().click();

  // Friendica redirects to /profile/<nick> after a successful post; verify
  // the post text shows up there. The /network feed only surfaces
  // contacts' posts, not your own.
  await page.goto(`${baseUrl}/profile/${biberUsername}`, { waitUntil: "domcontentloaded" });
  await expect(
    page.locator(".wall-item-body, .wall-item-content").filter({ hasText: statusText }).first(),
    "Expected Friendica profile timeline to surface the new status"
  ).toBeVisible({ timeout: 60_000 });
}

async function expectPostVisibleOnWall(page, wallUrl, needle, timeoutMs = 60000) {
  await page.goto(wallUrl);
  // Fediwall renders each post inside `<div class="wall-item">` (Vue
  // SPA component) — that is the stable container the test should
  // match against, NOT a generic `.post` class.
  await expect(
    page.locator(".wall-item").filter({ hasText: needle }).first(),
    `Expected a wall-item containing "${needle}" on ${wallUrl}`
  ).toBeVisible({ timeout: timeoutMs });
}

async function expectPostAbsentFromWall(page, wallUrl, needle, settleMs = 30000) {
  await page.goto(wallUrl);
  // Give Fediwall a full fetch interval to settle, then assert the
  // needle never appears. The microblog wall's cfg.interval=10s, so
  // 30s comfortably covers two refreshes.
  await page.waitForTimeout(settleMs);
  await expect(
    page.locator(".wall-item").filter({ hasText: needle }),
    `Expected NO wall-item containing "${needle}" on ${wallUrl}`
  ).toHaveCount(0);
}

// Strip scheme + path from a base URL to recover the bare host that
// fediwall's wall-config.json lists in `servers`.
function urlHost(url) {
  return new URL(url).host;
}

test("each wall surfaces biber's posts according to its servers list", async ({
  browser,
  request,
}) => {
  skipUnlessServiceEnabled("mastodon");
  skipUnlessServiceEnabled("friendica");

  const stamp = Date.now();
  // Driver per source app: how to post + which host the wall config
  // would list when this sibling is enabled.
  const siblings = [
    {
      name: "mastodon",
      host: urlHost(mastodonBaseUrl),
      status: `fediwall-e2e mastodon ${stamp}`,
      post: (page) => postOnMastodonViaUi(page, mastodonBaseUrl, `fediwall-e2e mastodon ${stamp}`),
    },
    {
      name: "friendica",
      host: urlHost(friendicaBaseUrl),
      status: `fediwall-e2e friendica ${stamp}`,
      post: (page) => postOnFriendicaViaUi(page, friendicaBaseUrl, `fediwall-e2e friendica ${stamp}`),
    },
  ];

  // Post once per sibling — isolated browser contexts so the OIDC
  // session for Mastodon and the ldapauth session for Friendica do
  // not bleed cookies/storage across.
  for (const s of siblings) {
    const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
    try {
      await s.post(await ctx.newPage());
    } finally {
      await ctx.close().catch(() => {});
    }
  }

  // For every deployed wall: read its servers list and assert that
  // each sibling's post appears iff its host is in `servers`.
  for (const slug of wallSlugs) {
    const cfgRes = await request.get(`${appBaseUrl}/${slug}/wall-config.json`);
    expect(
      cfgRes.ok(),
      `wall-config.json for slug='${slug}' must be reachable`
    ).toBeTruthy();
    const cfg = await cfgRes.json();
    const wallHosts = new Set(cfg.servers || []);

    const wallCtx = await browser.newContext({ ignoreHTTPSErrors: true });
    try {
      const wallPage = await wallCtx.newPage();
      for (const s of siblings) {
        const wallUrl = `${appBaseUrl}/${slug}/`;
        if (wallHosts.has(s.host)) {
          await expectPostVisibleOnWall(wallPage, wallUrl, s.status);
        } else {
          await expectPostAbsentFromWall(wallPage, wallUrl, s.status);
        }
      }
    } finally {
      await wallCtx.close().catch(() => {});
    }
  }
});
