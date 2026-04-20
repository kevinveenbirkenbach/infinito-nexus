const { test, expect } = require("@playwright/test");

test.use({ ignoreHTTPSErrors: true });
// Matrix SSO has several long-tail failure modes (Synapse rc_login rate
// limits, Element rust_crypto "Skip verification" dialog, first-run Synapse
// consent page, transient #/login bounce). The signIn helper walks through
// each with generous per-step waits, so the default 300s budget is far too
// tight — the DM test signs in twice and, when the prior per-user OIDC
// tests in the same spec have drained Synapse's rc_login burst, each
// sign-in can spend 5+ minutes cycling through consent↔M_LIMIT_EXCEEDED
// ping-pong before authenticating. 1200s (20 min) covers the worst case.
test.setTimeout(1_200_000);

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
  // Match only the full "Content Security Policy" phrase Chromium emits on
  // real CSP violations. An `|csp` alternative false-positives on random
  // base64/base58 strings (e.g. Matrix event_ids can contain "csP" as a
  // substring) that Element logs verbatim from matrix_sdk_crypto decrypt
  // warnings. The securitypolicyviolation DOM event in
  // installCspViolationObserver is the canonical source anyway.
  page.on("console", (m) => {
    if (m.type() === "error") consoleErrors.push(m.text());
    if (/content security policy/i.test(m.text())) {
      cspRelated.push({ source: "console", text: m.text() });
    }
  });
  page.on("pageerror", (e) => {
    const text = String(e);
    pageErrors.push(text);
    if (/content security policy/i.test(text)) {
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
  expect(cspHeader, `${label}: CSP response header MUST be present`).toBeTruthy();
  const reportOnly = headers["content-security-policy-report-only"];
  expect(reportOnly, `${label}: CSP-Report-Only MUST NOT be set`).toBeFalsy();
  const parsed = parseCspHeader(cspHeader);
  const missing = EXPECTED_CSP_DIRECTIVES.filter((d) => !parsed[d]);
  expect(missing, `${label}: CSP directives missing: ${missing.join(", ")}`).toEqual([]);
  return parsed;
}

async function expectNoCspViolations(page, diagnostics, label) {
  const domViolations = await readCspViolations(page);
  expect(domViolations, `${label}: securitypolicyviolation: ${JSON.stringify(domViolations)}`).toEqual([]);
  expect(diagnostics.cspRelated, `${label}: CSP console/pageerror: ${JSON.stringify(diagnostics.cspRelated)}`).toEqual([]);
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
const elementBaseUrl = normalizeBaseUrl(process.env.ELEMENT_BASE_URL || "");
const matrixBaseUrl = normalizeBaseUrl(process.env.MATRIX_BASE_URL || "");
const matrixServerName = decodeDotenvQuotedValue(process.env.MATRIX_SERVER_NAME);
const adminUsername = decodeDotenvQuotedValue(process.env.ADMIN_USERNAME);
const adminPassword = decodeDotenvQuotedValue(process.env.ADMIN_PASSWORD);
const biberUsername = decodeDotenvQuotedValue(process.env.BIBER_USERNAME);
const biberPassword = decodeDotenvQuotedValue(process.env.BIBER_PASSWORD);
const canonicalDomain = decodeDotenvQuotedValue(process.env.CANONICAL_DOMAIN);

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  expect(dashboardBaseUrl, "APP_BASE_URL must be set").toBeTruthy();
  expect(oidcIssuerUrl, "OIDC_ISSUER_URL must be set").toBeTruthy();
  expect(elementBaseUrl, "ELEMENT_BASE_URL must be set").toBeTruthy();
  expect(matrixBaseUrl, "MATRIX_BASE_URL must be set").toBeTruthy();
  expect(matrixServerName, "MATRIX_SERVER_NAME must be set").toBeTruthy();
  expect(adminUsername, "ADMIN_USERNAME must be set").toBeTruthy();
  expect(adminPassword, "ADMIN_PASSWORD must be set").toBeTruthy();
  expect(biberUsername, "BIBER_USERNAME must be set").toBeTruthy();
  expect(biberPassword, "BIBER_PASSWORD must be set").toBeTruthy();
  expect(canonicalDomain, "CANONICAL_DOMAIN must be set").toBeTruthy();
  await page.context().clearCookies();
  await installCspViolationObserver(page);
});

test("matrix element enforces Content-Security-Policy and exposes canonical domain from applications lookup", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);
  const response = await page.goto(`${elementBaseUrl}/`);
  expect(response, "Expected element landing response").toBeTruthy();
  expect(response.status(), "Expected element landing status < 400").toBeLessThan(400);
  assertCspResponseHeader(response, "matrix element landing");
  const documentUrl = response.url();
  expect(
    documentUrl.includes(canonicalDomain),
    `Expected canonical domain "${canonicalDomain}" to back the element URL`
  ).toBe(true);
  await expectNoCspViolations(page, diagnostics, "matrix element landing");
});

// Matrix Element SSO flow. Element stores the selected homeserver in
// sessionStorage during SSO initiation and reads it back when consuming the
// `?loginToken=…` the homeserver hands it after Keycloak auth. Hitting
// `/_matrix/client/v3/login/sso/redirect/<idp>` directly bypasses that
// sessionStorage write, which causes Element to fail with "your browser has
// forgotten which homeserver you use" when the loginToken returns. Therefore
// SSO must be initiated from Element's own login page so Element sets
// sessionStorage itself before redirecting to Synapse.
async function signInViaElementOidc(page, username, password, personaLabel) {
  const expectedOidcAuthUrl = `${oidcIssuerUrl}/protocol/openid-connect/auth`;

  await page.goto(`${dashboardBaseUrl}/`);
  await expect(page.locator("body"), `${personaLabel}: dashboard body`).toBeVisible({ timeout: 60_000 });

  await page.goto(`${elementBaseUrl}/#/login`);

  const ssoButton = page
    .locator(
      [
        ".mx_SSOButton",
        "[data-testid='sso-button']",
        "button[aria-label*='SSO' i]",
        "a[href*='/_matrix/client/v3/login/sso/redirect']"
      ].join(", ")
    )
    .first();
  const ssoTextButton = page
    .locator("button, a, div[role='button']")
    .filter({ hasText: /single\s*sign[- ]*on|continue\s+with\s+(sso|oidc|keycloak|openid)|sign\s+in\s+with\s+(sso|oidc|keycloak|openid)/i })
    .first();
  const candidate = (await ssoButton.isVisible({ timeout: 15_000 }).catch(() => false))
    ? ssoButton
    : ssoTextButton;
  await expect(candidate, `${personaLabel}: Element SSO entry button on #/login must be visible`).toBeVisible({ timeout: 30_000 });
  await candidate.click();

  await page.waitForURL((u) => u.toString().includes(expectedOidcAuthUrl), {
    timeout: 120_000
  });

  await performOidcLogin(page, username, password);

  // Synapse renders an "Continue to your account" confirmation page after the
  // Keycloak callback, with a "Continue" link pointing at
  // `<elementBaseUrl>/?loginToken=…`. The link must be clicked to hand the
  // token to Element. First-time logins also display a username-selection form
  // asking the user to pick their Matrix localpart before this confirmation.
  const usernameSelectField = page.locator("input[name='username'], input#field-username").first();
  if (await usernameSelectField.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await usernameSelectField.fill(username);
    const submit = page.locator("button[type='submit'], input[type='submit']").first();
    await submit.click();
  }

  const continueLink = page
    .locator("a, button")
    .filter({ hasText: /^\s*continue\s*$/i })
    .first();
  await expect(continueLink, `${personaLabel}: Synapse SSO confirmation "Continue" link must appear`).toBeVisible({ timeout: 60_000 });
  await continueLink.click();

  // Element consumes `?loginToken=…` during SPA bootstrap. The token is
  // single-use so we wait until Element has consumed it and navigated to an
  // authenticated SPA route (#/home, #/room/..., #/welcome — NOT #/login).
  // Including #/login in the accepted set would hide a failed token exchange.
  await page.waitForURL((u) => {
    const url = u.toString();
    if (!url.startsWith(elementBaseUrl)) return false;
    if (url.includes("loginToken=")) return false;
    if (url.includes("/_matrix/")) return false;
    if (url.includes(expectedOidcAuthUrl)) return false;
    if (/#\/login(\/|$|\?)/.test(url)) return false;
    if (/#\/welcome/.test(url) || /#\/home/.test(url) || /#\/room/.test(url) || url === `${elementBaseUrl}/` || url === `${elementBaseUrl}/#/`) return true;
    return false;
  }, { timeout: 120_000 });

  // With `feature_rust_crypto: true`, Element renders a full-screen "Confirm
  // your digital identity" / "Skip verification for now" interstitial on each
  // new-device login after the account has been provisioned. This interstitial
  // appears *asynchronously* once Element's crypto module finishes bootstrap
  // (not immediately on SPA load). We loop: whichever appears first wins —
  // authenticated UI (no interstitial) or Skip button (click, then continue).
  // Element renders the skip button as `<h1><button><img/></button></h1>` —
  // the visible text "Skip verification for now" lives on the heading (or as
  // an accessible name on the button), not inside the button's textContent.
  // Use ARIA role/name so the locator matches via accessibility tree.
  const skipVerificationButton = page.getByRole("button", { name: /skip\s+verification\s+for\s+now/i }).first();
  // Poll for any authenticated-UI signal directly in the DOM / ARIA tree.
  // Using page.evaluate avoids Locator strictness quirks and is orders of
  // magnitude faster than repeated `locator.isVisible()` round-trips.
  async function authenticatedSignalPresent() {
    return await page.evaluate(() => {
      if (document.querySelector(".mx_RoomList, .mx_UserMenu")) return true;
      const byAccessibleName = (roles, nameRegex) => {
        const selector = roles.map(r => `[role="${r}"]`).join(",");
        const nodes = document.querySelectorAll(selector);
        for (const n of nodes) {
          const name = (n.getAttribute("aria-label") || n.textContent || "").trim();
          if (nameRegex.test(name)) return true;
        }
        return false;
      };
      if (byAccessibleName(["button"], /^user menu$/i)) return true;
      if (byAccessibleName(["navigation"], /^room list$/i)) return true;
      if (byAccessibleName(["tree"], /^spaces$/i)) return true;
      const headings = document.querySelectorAll("h1");
      for (const h of headings) {
        if (/^\s*welcome\s+/i.test(h.textContent || "")) return true;
      }
      return false;
    }).catch(() => false);
  }

  // Element shows a non-blocking but pointer-event-capturing "Failed to load
  // service worker" alert in the Playwright browser (no SW support). If we
  // don't dismiss it, the #mx_Dialog_Container background intercepts clicks
  // on SSO / skip buttons and looks identical to the page hanging. It is
  // rendered as role="alert" (not role="dialog"). We both click the OK
  // button AND force-remove the lingering #mx_Dialog_Container so a stale
  // backdrop cannot block subsequent interactions.
  async function dismissServiceWorkerAlert() {
    await page.evaluate(() => {
      const alerts = document.querySelectorAll('[role="alert"], #mx_Dialog_Container');
      for (const a of alerts) {
        if (!/service worker/i.test(a.textContent || "")) continue;
        const btns = a.querySelectorAll("button");
        for (const b of btns) {
          if (/^\s*ok\s*$/i.test(b.textContent || "")) {
            b.click();
          }
        }
      }
      // Belt-and-braces: if a dialog backdrop is still lingering and has no
      // actionable content (i.e. it is only a stale service-worker alert
      // overlay), remove it so it stops eating clicks.
      document.querySelectorAll("#mx_Dialog_Container").forEach((el) => {
        if (/service worker/i.test(el.textContent || "") || !el.querySelector("button, input, textarea")) {
          el.remove();
        }
      });
    }).catch(() => {});
  }

  // Element may cycle through several states after SSO completes:
  // (a) directly to authenticated UI (room list),
  // (b) through the "Confirm your digital identity" / Skip dialog (rust_crypto
  //     on a new device),
  // (c) bounce back to #/login (token race / sync error / transient issue) —
  //     in which case we need to re-trigger SSO from the login page.
  // Poll state every few seconds up to an overall deadline, handling each
  // case, rather than racing individual waits.
  // Handle Synapse's rc_login rate limit. When Element gets
  // `M_LIMIT_EXCEEDED` during SSO token exchange, it shows a modal with a
  // "Try again" button and keeps the user on its own #/login page. The only
  // way forward is to wait out the rate-limit window (Synapse default drains
  // at 0.17/s) and click "Try again". Waiting less just re-triggers the
  // failure; clicking immediately is counterproductive.
  async function retryOnRateLimitDialog() {
    // Match specifically on the `M_LIMIT_EXCEEDED` error code string (which
    // Element includes verbatim in the dialog body). Matching on
    // "couldn't log you in" alone is too loose — Element uses the same
    // phrasing for non-rate-limit SSO errors, and waiting out a 45s cooldown
    // then clicking "Try again" only helps for rc_login exhaustion.
    const rateLimitDialog = page.getByRole("dialog").filter({ hasText: /M_LIMIT_EXCEEDED/ });
    if (!(await rateLimitDialog.isVisible().catch(() => false))) return false;
    // Synapse's default rc_login drains at ~0.17/s (≈6s per slot) with a
    // burst of 3. After the burst is exhausted, recovery of a usable slot
    // requires a few seconds per slot. Wait 45s to leave margin — clicking
    // "Try again" sooner just re-triggers M_LIMIT_EXCEEDED and burns the
    // next burst slot, extending the outage.
    await page.waitForTimeout(45_000);
    const tryAgain = rateLimitDialog.getByRole("button", { name: /^try again$/i }).first();
    await tryAgain.click({ timeout: 5_000 }).catch(() => {});
    return true;
  }

  // Synapse shows an interstitial "Continue to your account" consent page
  // (`/_synapse/client/sso/redirect/confirm`) on first SSO login for a given
  // account/client pair. The only way forward is a "Continue" link that
  // carries the `?loginToken=` callback URL. Element never renders this page
  // itself — it lives on the Synapse domain — so auth signals will never
  // appear here.
  //
  // Important: if we click "Continue" and Element's subsequent /login call
  // hits Synapse's `rc_login` burst, Element silently re-triggers SSO, which
  // dumps us back on the consent page with a fresh loginToken. Spamming
  // "Continue" each poll iteration burns rc_login slots and turns into an
  // unrecoverable loop. Rate-limit the click to one attempt per ≥30s so
  // rc_login has time to drain between retries.
  let lastConsentClickAt = 0;
  async function passSynapseConsentPage() {
    const heading = page.getByRole("heading", { name: /continue to your account/i });
    if (!(await heading.isVisible().catch(() => false))) return false;
    const now = Date.now();
    if (now - lastConsentClickAt < 30_000) return true;
    // Synapse's consent template historically used an `<a>` link but now
    // ships a `<button>` as the primary action. Match both via role-based
    // lookup AND a DOM-level fallback so the handler keeps working across
    // Synapse template revisions. Using `a, button` with a text filter is
    // more robust than `getByRole("link"|"button")` alone because Synapse
    // sometimes emits a native submit without an accessible name match.
    const continueAction = page
      .locator("a[href*='loginToken=']")
      .or(page.locator("a, button, input[type='submit']").filter({ hasText: /^\s*continue\s*$/i }))
      .first();
    const clickResult = await continueAction
      .click({ timeout: 10_000 })
      .then(() => "ok")
      .catch((e) => e.message || "click-failed");
    // Only throttle subsequent attempts when the click actually landed.
    // A failed click (locator missed, overlay intercepted, etc.) must not
    // burn the 30s cooldown — otherwise the whole state deadline can
    // expire without ever advancing.
    if (clickResult === "ok") lastConsentClickAt = now;
    return true;
  }

  // 360s (6 minutes) covers the worst case: Synapse rc_login drains at
  // 0.17/s with 3 burst slots, and Element's consent ↔ M_LIMIT_EXCEEDED
  // ping-pong can cost ~75s per cycle (30s consent cool-down + 45s rate
  // limit cool-down). 240s wasn't enough when rc_login was already drained
  // by prior tests in the same spec run.
  const stateDeadline = Date.now() + 360_000;
  while (Date.now() < stateDeadline) {
    await dismissServiceWorkerAlert();
    if (await authenticatedSignalPresent()) break;
    if (await passSynapseConsentPage()) continue;
    if (await retryOnRateLimitDialog()) continue;
    if (await skipVerificationButton.isVisible().catch(() => false)) {
      await skipVerificationButton.click({ timeout: 5_000 }).catch(() => {});
      // Element may show a secondary confirm dialog for the skip choice.
      // MUST NOT click "Reset identity" — that destroys the device identity
      // and logs the user back out to #/login.
      const confirmSkip = page
        .getByRole("button", { name: /^\s*(skip(\s+anyway)?|i'?ll\s+verify\s+later|continue)\s*$/i })
        .first();
      await confirmSkip.waitFor({ state: "visible", timeout: 5_000 }).catch(() => {});
      if (await confirmSkip.isVisible().catch(() => false)) {
        await confirmSkip.click({ timeout: 5_000 }).catch(() => {});
      }
      await page.waitForTimeout(2_000);
      continue;
    }
    // If Element has bounced back to its own #/login page AND no auth signal
    // is yet present, re-trigger SSO.
    if (/#\/login(\/|$|\?)/.test(page.url())) {
      const ssoRetry = page
        .locator(
          [
            ".mx_SSOButton",
            "[data-testid='sso-button']",
            "a[href*='/_matrix/client/v3/login/sso/redirect']"
          ].join(", ")
        )
        .or(page.getByRole("button", { name: /continue\s+with\s+sso|single\s*sign[- ]*on/i }))
        .first();
      if (await ssoRetry.isVisible().catch(() => false)) {
        // Short click timeout: if the click is blocked (e.g. by a stale
        // backdrop), we want to fall back to the next poll iteration quickly
        // rather than burning the entire test budget on click-retry.
        await ssoRetry.click({ timeout: 5_000 }).catch(() => {});
        await page.waitForURL((u) => !/#\/login(\/|$|\?)/.test(u.toString()), { timeout: 30_000 }).catch(() => {});
      }
    }
    await page.waitForTimeout(2_000);
  }

  // Final gate: poll the DOM a few more times. If any of our signals show
  // up, we're authenticated. Otherwise, fail with a descriptive message.
  await expect
    .poll(authenticatedSignalPresent, {
      timeout: 60_000,
      message: `${personaLabel}: authenticated Element UI (user menu / room list / welcome) must render`
    })
    .toBe(true);
}

test("administrator: dashboard to matrix element OIDC login and logout", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);
  await signInViaElementOidc(page, adminUsername, adminPassword, "administrator");
  await expectNoCspViolations(page, diagnostics, "matrix element administrator OIDC");
});

test("biber: dashboard to matrix element OIDC login and logout", async ({ page }) => {
  const diagnostics = attachDiagnostics(page);
  await signInViaElementOidc(page, biberUsername, biberPassword, "biber");
  await expectNoCspViolations(page, diagnostics, "matrix element biber OIDC");
});

test.describe("matrix DM", () => {
  // rc_login exhaustion used to be the dominant failure mode here (retries
  // burned through Synapse's default burst of 3), which is why this block
  // previously set retries=0. The 120s drain wait before admin's signin
  // below made that obsolete. The dominant failure mode is now transient
  // CI infra pressure — browser processes getting OOM-killed under the
  // combined load of Synapse + Element + bridges + Keycloak + Mailu +
  // Matomo on a standard runner surfaces as "Target page, context or
  // browser has been closed" mid-navigation. Allow a single retry so those
  // transient crashes don't fail the suite. Cap at 1 (not the config-wide
  // 2) so a genuinely broken test can't burn 3× the DM budget (~9m).
  test.describe.configure({ retries: 1 });

  test("administrator and biber can exchange a direct message in element", async ({ browser }) => {
    const adminContext = await browser.newContext({ ignoreHTTPSErrors: true });
    const biberContext = await browser.newContext({ ignoreHTTPSErrors: true });
    const adminPage = await adminContext.newPage();
    const biberPage = await biberContext.newPage();

    await installCspViolationObserver(adminPage);
    await installCspViolationObserver(biberPage);

    // When the spec runs in full (CSP + two per-user OIDC tests + DM), the
    // prior admin/biber logins have already consumed Synapse's rc_login
    // burst (default: 3 slots, drain 0.17/s ≈ 6s per slot). The per-user
    // OIDC tests themselves can take minutes and trigger retries that
    // consume additional slots. Waiting ~120s before DM's admin sign-in
    // lets the burst and any pending retries fully drain, so the DM
    // test's state machine isn't forced to spend most of its deadline
    // cycling through consent↔M_LIMIT_EXCEEDED retries. Running the DM
    // test in isolation doesn't need this, but the extra wait is cheap.
    await adminPage.waitForTimeout(120_000);
    await signInViaElementOidc(adminPage, adminUsername, adminPassword, "administrator");
    // Same reasoning between admin and biber: two back-to-back SSO
    // logins easily exhaust rc_login. 30s lets the burst refill.
    await adminPage.waitForTimeout(30_000);
    await signInViaElementOidc(biberPage, biberUsername, biberPassword, "biber");

  const marker = `hello-from-admin-${Date.now()}`;
  // MXIDs use the Synapse server_name (a.k.a. MATRIX_SERVER_NAME, typically
  // the bare DOMAIN_PRIMARY), not the client-facing URL host. Using the URL
  // host (e.g. "matrix.infinito.example") yields a non-existent user and
  // Synapse returns HTTP 502 on profile lookup.
  const biberMatrixId = `@${biberUsername}:${matrixServerName}`;

  // Admin opens a DM to biber via URL API (#/user/@biber:...). This renders
  // biber's profile in a right-hand `aside` panel alongside the home
  // welcome screen — not a full-screen user view — so the "Send message"
  // button we need lives inside the profile panel specifically (there is a
  // separate "Send a Direct Message" button on the welcome screen that
  // opens a search dialog rather than directly messaging biber).
  await adminPage.goto(`${elementBaseUrl}/#/user/${encodeURIComponent(biberMatrixId)}`);

  const profilePanel = adminPage.getByRole("complementary").filter({ hasText: biberMatrixId });
  await expect(profilePanel, "admin: biber profile panel must render").toBeVisible({ timeout: 60_000 });

  const profileSendMessageButton = profilePanel
    .getByRole("button", { name: /^send message$/i })
    .first();
  await expect(profileSendMessageButton, "admin: profile 'Send message' button must be visible").toBeVisible({ timeout: 30_000 });
  await profileSendMessageButton.click();

  // After clicking "Send message", Element navigates into the DM room and
  // renders a message composer. Wait for the room header to show biber's
  // name before looking for the composer, so we don't match a stale
  // textbox from the previous view (e.g. a search field).
  const roomHeader = adminPage.getByRole("heading", { name: /harry beaver|biber/i }).first();
  await expect(roomHeader, "admin: DM room header with biber must render").toBeVisible({ timeout: 30_000 });

  const composer = adminPage
    .locator("div[role='textbox'][contenteditable='true'], textarea[aria-label*='message' i], div[aria-label*='message' i][contenteditable='true']")
    .last();
  await expect(composer, "admin: message composer must appear").toBeVisible({ timeout: 60_000 });
  await composer.click();

  // Element keeps the DM in a pending "Send your first message to invite …"
  // state when entered via a profile's "Send message" button: the room
  // (and therefore the invite to biber) is only created on the server once
  // admin actually sends. Without this bootstrap send, biber's side never
  // receives an invite tile and the accept-invite poll below times out.
  //
  // The bootstrap text is intentionally distinct from `marker`. With E2EE
  // enabled and biber not yet joined, this first ciphertext will land on
  // biber's side as "Unable to decrypt message" (no pre-join megolm key
  // share). That's acceptable — biber's assertion targets `marker`, which
  // admin sends AFTER biber has joined so Element establishes a fresh
  // outbound megolm session that includes biber's device.
  const bootstrap = `bootstrap-${Date.now()}`;
  await adminPage.keyboard.type(bootstrap);
  await adminPage.keyboard.press("Enter");

  // Biber: wait for admin's invite to propagate, then accept. The flow
  // mirrors Element's invite UX: (1) click the sidebar tile for admin's
  // invite (the tile renders with admin's display name but no standalone
  // Accept button), then (2) click the primary accept action in the invite
  // view (modern Element labels this "Start chatting" for DMs; older
  // builds / non-DM invites use "Accept" / "Join"). MUST NOT match
  // "Decline" / "Decline and block".
  await expect
    .poll(async () => {
      return await biberPage.evaluate(() => {
        // Step 1: open the invite.
        const roomTiles = document.querySelectorAll(
          "[role='treeitem'], [role='option'], .mx_RoomTile, [data-testid^='room-tile']"
        );
        for (const tile of roomTiles) {
          const text = (tile.textContent || "").trim();
          if (/administrator/i.test(text)) {
            tile.click();
            break;
          }
        }
        // Step 2: click accept.
        const acceptCandidates = document.querySelectorAll(
          "button, a, [role='button']"
        );
        for (const b of acceptCandidates) {
          const text = (b.textContent || "").trim();
          if (/^(start chatting|accept|accept invite|join|annehmen|akzeptieren)$/i.test(text)) {
            b.click();
          }
        }
        // Success: invite accepted when the room timeline renders a
        // message composer for biber (only appears once membership is
        // `join`). Use the same composer signature as admin's side.
        return !!document.querySelector(
          "div[role='textbox'][contenteditable='true'], textarea[aria-label*='message' i]"
        );
      }).catch(() => false);
    }, {
      timeout: 120_000,
      message: "biber: expected invite acceptance to produce a message composer"
    })
    .toBe(true);

  // Give admin's client a moment to observe biber's join and establish a
  // megolm session before sending the marker. Element batches outbound
  // session creation on membership events; 5s is generous.
  await adminPage.waitForTimeout(5_000);
  await composer.click();
  await adminPage.keyboard.type(marker);
  await adminPage.keyboard.press("Enter");

  // Biber should now receive the marker as a live (not historical)
  // message and decrypt it via the just-shared megolm session.
  await expect
    .poll(async () => {
      return (await biberPage.locator("body").innerText().catch(() => "")).includes(marker);
    }, {
      timeout: 120_000,
      message: `biber: expected to receive message "${marker}" from administrator`
    })
    .toBe(true);

    await adminContext.close();
    await biberContext.close();
  });
});
