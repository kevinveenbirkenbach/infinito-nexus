/*
 * Bluesky login-broker.
 *
 * Architecture (variant A+ per requirement 013, web-app-bluesky):
 *
 *     Browser
 *       │
 *       │  https://web.bluesky.<DOMAIN>/...
 *       ▼
 *     nginx (front-proxy)
 *       │
 *       ▼
 *     oauth2-proxy ── (Keycloak OIDC) ──► Keycloak realm
 *       │
 *       │  forward + X-Forwarded-User / X-Forwarded-Email
 *       ▼
 *     login-broker (this process)
 *       │
 *       │  - Auto-provision PDS account on first visit
 *       │    via com.atproto.server.createAccount
 *       │  - Encrypt the synthesised app-password with AES-256-GCM
 *       │    and store it as a Keycloak user attribute
 *       │  - Decrypt the password, call createSession against the PDS
 *       │  - Render an HTML handoff page that drops the resulting
 *       │    session JWTs into localStorage["BSKY_STORAGE"] and
 *       │    redirects to "/" (the social-app)
 *       ▼
 *     social-app  (the official @bluesky-social/social-app web UI)
 *
 * The encrypted app-password never leaves the broker as cleartext
 * over the wire; the synthesised password lives encrypted-at-rest in
 * Keycloak and is only decrypted in-process when needed for a
 * createSession call. This is the scope of the encryption hardening
 * agreed in the autonomous iteration with the operator (no plaintext
 * in Keycloak).
 *
 * Future hardening (out-of-scope for this iteration, tracked in the
 * doc 013 "Future Hardening" section): rotating the encryption key,
 * moving the app-password into an external secrets store, and
 * registering a Keycloak event-listener SPI so the encrypted
 * attribute also lives on the user record in case the broker is
 * down.
 */

"use strict";

const http = require("node:http");
const https = require("node:https");
const crypto = require("node:crypto");
const { URL } = require("node:url");

// --- Configuration --------------------------------------------------

const CONFIG = {
  listenPort: parseInt(process.env.BROKER_PORT || "8080", 10),
  socialAppUrl: requireEnv("SOCIAL_APP_URL"),
  pdsUrl: requireEnv("PDS_URL"),
  pdsHandleDomain: requireEnv("PDS_HANDLE_DOMAIN"),
  pdsInviteCode: process.env.PDS_INVITE_CODE || "",
  kcAdminBaseUrl: requireEnv("KC_ADMIN_BASE_URL"),
  kcAdminRealm: requireEnv("KC_ADMIN_REALM"),
  kcAdminClientId: requireEnv("KC_ADMIN_CLIENT_ID"),
  kcAdminClientSecret: requireEnv("KC_ADMIN_CLIENT_SECRET"),
  kcUserRealm: requireEnv("KC_USER_REALM"),
  encryptionKey: decodeKey(requireEnv("BLUESKY_BRIDGE_ENCRYPTION_KEY")),
  handoffCookieName: process.env.HANDOFF_COOKIE_NAME || "bsky_handoff_done",
  handoffCookieMaxAgeSec: parseInt(process.env.HANDOFF_COOKIE_MAX_AGE || "3300", 10),
  insecureTls: (process.env.INSECURE_TLS || "false").toLowerCase() === "true",
  logoutPath: "/sso/logout"
};

function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env: ${name}`);
  }
  return value;
}

function decodeKey(value) {
  // Accept the project-canonical `base64:<...>` prefix (algorithm
  // `base64_prefixed_32` in meta/schema.yml) so the same vaulted
  // value flows through the env without further mangling.
  let b64 = value || "";
  if (b64.startsWith("base64:")) b64 = b64.slice(7);
  const buf = Buffer.from(b64, "base64");
  if (buf.length !== 32) {
    throw new Error(`BLUESKY_BRIDGE_ENCRYPTION_KEY must decode to 32 bytes, got ${buf.length}`);
  }
  return buf;
}

// --- AES-256-GCM helpers --------------------------------------------

function encrypt(plaintext) {
  const nonce = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", CONFIG.encryptionKey, nonce);
  const ct = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([nonce, ct, tag]).toString("base64");
}

function decrypt(b64) {
  const blob = Buffer.from(b64, "base64");
  if (blob.length < 12 + 16) {
    throw new Error("ciphertext too short");
  }
  const nonce = blob.subarray(0, 12);
  const tag = blob.subarray(blob.length - 16);
  const ct = blob.subarray(12, blob.length - 16);
  const decipher = crypto.createDecipheriv("aes-256-gcm", CONFIG.encryptionKey, nonce);
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(ct), decipher.final()]).toString("utf8");
}

// --- HTTP helpers ---------------------------------------------------

function fetchJson(method, urlString, opts = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(urlString);
    const isHttps = u.protocol === "https:";
    const lib = isHttps ? https : http;
    const headers = Object.assign({ "Accept": "application/json" }, opts.headers || {});
    let body = opts.body;
    if (body && typeof body !== "string" && !(body instanceof Buffer)) {
      body = JSON.stringify(body);
      headers["Content-Type"] = headers["Content-Type"] || "application/json";
    }
    if (body) {
      headers["Content-Length"] = Buffer.byteLength(body);
    }
    const req = lib.request({
      method,
      hostname: u.hostname,
      port: u.port || (isHttps ? 443 : 80),
      path: u.pathname + u.search,
      headers,
      rejectUnauthorized: !CONFIG.insecureTls
    }, (res) => {
      const chunks = [];
      res.on("data", (c) => chunks.push(c));
      res.on("end", () => {
        const buf = Buffer.concat(chunks);
        const ct = (res.headers["content-type"] || "").split(";")[0].trim();
        let parsed = null;
        if (buf.length > 0 && ct === "application/json") {
          try { parsed = JSON.parse(buf.toString("utf8")); } catch (_) { /* tolerate */ }
        }
        resolve({ status: res.statusCode || 0, body: parsed, raw: buf.toString("utf8") });
      });
    });
    req.on("error", reject);
    if (body) req.write(body);
    req.end();
  });
}

// --- Keycloak Admin API client --------------------------------------

let cachedAdminToken = null;
let cachedAdminTokenExpiry = 0;

async function getAdminToken() {
  const now = Math.floor(Date.now() / 1000);
  if (cachedAdminToken && cachedAdminTokenExpiry > now + 30) {
    return cachedAdminToken;
  }
  const tokenUrl =
    `${CONFIG.kcAdminBaseUrl}/realms/${encodeURIComponent(CONFIG.kcAdminRealm)}/protocol/openid-connect/token`;
  const form = new URLSearchParams({
    grant_type: "client_credentials",
    client_id: CONFIG.kcAdminClientId,
    client_secret: CONFIG.kcAdminClientSecret
  }).toString();
  const res = await fetchJson("POST", tokenUrl, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form
  });
  if (res.status !== 200 || !res.body || !res.body.access_token) {
    throw new Error(`Keycloak token request failed: status=${res.status} body=${res.raw}`);
  }
  cachedAdminToken = res.body.access_token;
  cachedAdminTokenExpiry = now + parseInt(res.body.expires_in || "60", 10);
  return cachedAdminToken;
}

async function findUser(username) {
  const token = await getAdminToken();
  const url =
    `${CONFIG.kcAdminBaseUrl}/admin/realms/${encodeURIComponent(CONFIG.kcUserRealm)}` +
    `/users?username=${encodeURIComponent(username)}&exact=true`;
  const res = await fetchJson("GET", url, { headers: { Authorization: `Bearer ${token}` } });
  if (res.status !== 200 || !Array.isArray(res.body)) {
    throw new Error(`Keycloak findUser failed: status=${res.status}`);
  }
  return res.body[0] || null;
}

async function updateUser(userId, partial) {
  const token = await getAdminToken();
  const url = `${CONFIG.kcAdminBaseUrl}/admin/realms/${encodeURIComponent(CONFIG.kcUserRealm)}` +
              `/users/${encodeURIComponent(userId)}`;
  const res = await fetchJson("PUT", url, {
    headers: { Authorization: `Bearer ${token}` },
    body: partial
  });
  if (res.status !== 204 && res.status !== 200) {
    throw new Error(`Keycloak updateUser failed: status=${res.status} body=${res.raw}`);
  }
}

// --- PDS client -----------------------------------------------------

function sanitiseHandle(username) {
  if (!username) return "user";
  const lower = username.toLowerCase();
  const mapped = lower.replace(/[^a-z0-9-]+/g, "-").replace(/^-+|-+$/g, "");
  return mapped || "user";
}

async function pdsCreateAccount({ handle, email, password }) {
  const url = `${CONFIG.pdsUrl}/xrpc/com.atproto.server.createAccount`;
  const body = { handle, email, password };
  if (CONFIG.pdsInviteCode) {
    body.inviteCode = CONFIG.pdsInviteCode;
  }
  const res = await fetchJson("POST", url, { body });
  if (res.status < 200 || res.status >= 300) {
    throw new Error(`PDS createAccount failed: status=${res.status} body=${res.raw}`);
  }
  return res.body;
}

async function pdsCreateSession({ handle, password }) {
  const url = `${CONFIG.pdsUrl}/xrpc/com.atproto.server.createSession`;
  const res = await fetchJson("POST", url, { body: { identifier: handle, password } });
  if (res.status < 200 || res.status >= 300) {
    throw new Error(`PDS createSession failed: status=${res.status} body=${res.raw}`);
  }
  return res.body;
}

// --- High-level orchestration --------------------------------------

const ATTR_APP_PASSWORD_ENC = "bluesky_app_password_enc";
const ATTR_DID = "bluesky_did";
const ATTR_HANDLE = "bluesky_handle";

function pickAttr(user, name) {
  if (!user || !user.attributes) return null;
  const v = user.attributes[name];
  if (Array.isArray(v) && v.length > 0) return v[0];
  return null;
}

async function ensurePdsSession({ kcUsername, kcEmail }) {
  const kcUser = await findUser(kcUsername);
  if (!kcUser) {
    throw new Error(`Keycloak user not found by username=${kcUsername}`);
  }
  const fullHandle = `${sanitiseHandle(kcUsername)}.${CONFIG.pdsHandleDomain}`;
  let appPasswordEnc = pickAttr(kcUser, ATTR_APP_PASSWORD_ENC);
  let did = pickAttr(kcUser, ATTR_DID);
  if (!appPasswordEnc) {
    const synthesised = crypto.randomBytes(18).toString("base64url");
    const created = await pdsCreateAccount({
      handle: fullHandle,
      email: kcEmail || `${kcUsername}@bridge.local`,
      password: synthesised
    });
    did = created.did || did;
    appPasswordEnc = encrypt(synthesised);
    await updateUser(kcUser.id, {
      attributes: Object.assign({}, kcUser.attributes || {}, {
        [ATTR_APP_PASSWORD_ENC]: [appPasswordEnc],
        [ATTR_DID]: did ? [did] : [],
        [ATTR_HANDLE]: [fullHandle]
      })
    });
  }
  const password = decrypt(appPasswordEnc);
  const session = await pdsCreateSession({ handle: fullHandle, password });
  return {
    service: CONFIG.pdsUrl,
    did: session.did || did,
    handle: session.handle || fullHandle,
    email: kcEmail || `${kcUsername}@bridge.local`,
    emailConfirmed: true,
    accessJwt: session.accessJwt,
    refreshJwt: session.refreshJwt
  };
}

// --- HTTP server ----------------------------------------------------

function parseCookies(req) {
  const out = {};
  const header = req.headers["cookie"];
  if (!header) return out;
  for (const part of header.split(";")) {
    const i = part.indexOf("=");
    if (i < 0) continue;
    out[part.slice(0, i).trim()] = decodeURIComponent(part.slice(i + 1).trim());
  }
  return out;
}

// Build a schema-compliant social-app storage payload (matches
// `bluesky-social/social-app@1.121.0` `state/persisted/schema.ts`
// defaults). Without ALL required keys present, social-app's
// `tryParse()` call uses zod `safeParse()` which returns failure
// and the persistence layer DROPS the entire stored value — the
// session never sticks. The `defaults` object below mirrors the
// upstream `defaults` constant verbatim plus our session.
function buildBskyStorage(session) {
  return {
    colorMode: "system",
    darkTheme: "dim",
    session: {
      accounts: [Object.assign({}, session, { active: true })],
      currentAccount: Object.assign({}, session, { active: true })
    },
    reminders: {},
    languagePrefs: {
      primaryLanguage: "en",
      contentLanguages: ["en"],
      postLanguage: "en",
      postLanguageHistory: ["en", "ja", "pt", "de"],
      appLanguage: "en"
    },
    requireAltTextEnabled: false,
    largeAltBadgeEnabled: false,
    externalEmbeds: {},
    mutedThreads: [],
    invites: { copiedInvites: [] },
    onboarding: { step: "Home" },
    hiddenPosts: [],
    pdsAddressHistory: [],
    disableHaptics: false,
    disableAutoplay: false,
    kawaii: false,
    hasCheckedForStarterPack: false,
    subtitlesEnabled: true,
    trendingDisabled: false,
    trendingVideoDisabled: false
  };
}

function renderHandoff(session, redirectTo) {
  const storageJson = JSON.stringify(buildBskyStorage(session));
  const safeRedirect = JSON.stringify(redirectTo || "/");
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Bluesky SSO handoff</title>
<meta name="referrer" content="no-referrer" />
<style>body{font-family:sans-serif;background:#001a33;color:#eef;margin:0;padding:2em;text-align:center}</style>
</head>
<body>
<p id="status">Signing you in to Bluesky…</p>
<script>
(function(){
  try {
    var storage = ${storageJson};
    localStorage.setItem("BSKY_STORAGE", JSON.stringify(storage));
    document.cookie = ${JSON.stringify(CONFIG.handoffCookieName)} + "=1; Path=/; Max-Age=" + ${JSON.stringify(CONFIG.handoffCookieMaxAgeSec)} + "; SameSite=Lax";
    window.location.replace(${safeRedirect});
  } catch (e) {
    document.getElementById("status").textContent = "SSO handoff error: " + (e && e.message ? e.message : e);
  }
})();
</script>
<noscript>This SSO handoff requires JavaScript.</noscript>
</body>
</html>`;
}

function endHtml(res, status, html) {
  res.writeHead(status, {
    "Content-Type": "text/html; charset=utf-8",
    "Cache-Control": "no-store"
  });
  res.end(html);
}

function endText(res, status, text, headers = {}) {
  res.writeHead(status, Object.assign({ "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" }, headers));
  res.end(text);
}

function proxyToSocialApp(req, res) {
  const upstream = new URL(CONFIG.socialAppUrl);
  const isHttps = upstream.protocol === "https:";
  const lib = isHttps ? https : http;
  const headers = Object.assign({}, req.headers);
  headers.host = upstream.host;
  const upstreamReq = lib.request({
    method: req.method,
    hostname: upstream.hostname,
    port: upstream.port || (isHttps ? 443 : 80),
    path: req.url,
    headers,
    rejectUnauthorized: !CONFIG.insecureTls
  }, (upstreamRes) => {
    res.writeHead(upstreamRes.statusCode || 502, upstreamRes.headers);
    upstreamRes.pipe(res);
  });
  upstreamReq.on("error", (err) => {
    endText(res, 502, `social-app upstream error: ${err.message}`);
  });
  req.pipe(upstreamReq);
}

const server = http.createServer(async (req, res) => {
  const reqId = Math.random().toString(36).slice(2, 8);
  const reqStart = Date.now();
  // eslint-disable-next-line no-console
  console.log(`[broker:${reqId}] ${req.method} ${req.url} from=${req.headers["x-forwarded-for"] || "?"} fwd-user=${req.headers["x-forwarded-user"] || req.headers["x-forwarded-preferred-username"] || "-"}`);
  try {
    const requestUrl = new URL(req.url, "http://internal");
    const path = requestUrl.pathname;

    if (path === "/healthz") {
      endText(res, 200, "ok");
      return;
    }
    if (path === CONFIG.logoutPath) {
      // Clear our handoff cookie and forward to oauth2-proxy sign_out
      // which itself bounces to the OIDC end-session endpoint.
      res.writeHead(302, {
        "Set-Cookie": `${CONFIG.handoffCookieName}=; Path=/; Max-Age=0; SameSite=Lax`,
        "Location": "/oauth2/sign_out"
      });
      res.end();
      return;
    }

    const cookies = parseCookies(req);
    if (cookies[CONFIG.handoffCookieName] === "1") {
      // eslint-disable-next-line no-console
      console.log(`[broker:${reqId}] handoff cookie present → proxying to social-app (${Date.now() - reqStart}ms)`);
      proxyToSocialApp(req, res);
      return;
    }

    // Need a fresh handoff. The OIDC identity comes from oauth2-proxy
    // forwarded headers — without them the broker cannot proceed and
    // the request is rejected.
    const kcUsername = (req.headers["x-forwarded-preferred-username"] || req.headers["x-forwarded-user"] || "").toString();
    const kcEmail = (req.headers["x-forwarded-email"] || "").toString();
    if (!kcUsername) {
      // eslint-disable-next-line no-console
      console.log(`[broker:${reqId}] missing X-Forwarded-User → 401 (${Date.now() - reqStart}ms)`);
      endText(res, 401, "Missing X-Forwarded-User from oauth2-proxy. Refusing handoff.");
      return;
    }

    const session = await ensurePdsSession({ kcUsername, kcEmail });
    // eslint-disable-next-line no-console
    console.log(`[broker:${reqId}] PDS session ready did=${session.did} handle=${session.handle} hasAccessJwt=${!!session.accessJwt} (${Date.now() - reqStart}ms)`);
    const html = renderHandoff(session, requestUrl.pathname + (requestUrl.search || ""));
    endHtml(res, 200, html);
    // eslint-disable-next-line no-console
    console.log(`[broker:${reqId}] handoff HTML sent (${Date.now() - reqStart}ms)`);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error(`[broker:${reqId}] error:`, err.stack || err.message);
    endText(res, 500, `Broker error: ${err.message}`);
  }
});

server.listen(CONFIG.listenPort, () => {
  // eslint-disable-next-line no-console
  console.log(`[broker] listening on ${CONFIG.listenPort}, social-app=${CONFIG.socialAppUrl}, pds=${CONFIG.pdsUrl}`);
});
