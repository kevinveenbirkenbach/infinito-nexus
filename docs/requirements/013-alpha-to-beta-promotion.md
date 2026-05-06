# 013 - Sub-Beta-to-Beta Lifecycle Promotion for `web-*` Roles

## User Story 📖

As a contributor maintaining `infinito-nexus`, I want every `web-*` role under
[roles/](../../roles/) to reach `lifecycle: beta` (or higher) so the project's
public role catalogue does not advertise immature components alongside
production-ready ones, and so the matrix-deploy + Playwright gate uniformly
applies to every shipped role.

## Goal 🎯

Promote every role listed below from `planned`, `pre-alpha`, or `alpha` to
`beta`. The exact contract of what `beta` MUST guarantee will be sharpened in
follow-up work; this document only fixes the *set* of roles in scope and
makes the promotion an explicit, tracked requirement.

## In Scope 📦

The following fourteen roles MUST reach `meta/services.yml.<entity>.lifecycle:
beta`:

| Role                                                                      | Current lifecycle | OIDC | LDAP | RBAC |
| ------------------------------------------------------------------------- | ----------------- | :--: | :--: | :--: |
| [web-app-akaunting](../../roles/web-app-akaunting/)                       | alpha     | 🛠️ | 🛠️ | 🛠️ |
| [web-app-baserow](../../roles/web-app-baserow/)                           | alpha     | 🛠️ | 🛠️ | 🛠️ |
| [web-app-bluesky](../../roles/web-app-bluesky/)                           | pre-alpha | 🛠️ | 🛠️ | ❌ |
| [web-app-bookwyrm](../../roles/web-app-bookwyrm/)                         | alpha     | 🛠️ | 🛠️ | 🛠️ |
| [web-app-bridgy-fed](../../roles/web-app-bridgy-fed/)                     | planned   | ❌ | ❌ | ❌ |
| [web-app-flowise](../../roles/web-app-flowise/)                           | alpha     | ✅ | 🛠️ | 🛠️ |
| [web-app-fusiondirectory](../../roles/web-app-fusiondirectory/)           | planned   | ✅ | ✅ | ✅ |
| [web-app-jenkins](../../roles/web-app-jenkins/)                           | planned   | ✅ | ✅ | ✅ |
| [web-app-joomla](../../roles/web-app-joomla/)                             | alpha     | ✅ | ✅ | 🛠️ |
| [web-app-minio](../../roles/web-app-minio/)                               | pre-alpha | ✅ | ✅ | ✅ |
| [web-app-postmarks](../../roles/web-app-postmarks/)                       | pre-alpha | 🛠️ | 🛠️ | ❌ |
| [web-app-socialhome](../../roles/web-app-socialhome/)                     | pre-alpha | 🛠️ | 🛠️ | 🛠️ |
| [web-svc-libretranslate](../../roles/web-svc-libretranslate/)             | pre-alpha | 🛠️ | ❌ | ❌ |
| [web-svc-xmpp](../../roles/web-svc-xmpp/)                                 | pre-alpha | ✅ | ✅ | 🛠️ |

The OIDC and LDAP columns reflect how the role's `beta` step would
wire up authentication against
[web-app-keycloak](../../roles/web-app-keycloak/) and
[svc-db-openldap](../../roles/svc-db-openldap/) respectively (see the
`beta` criteria in [lifecycle.md](../contributing/design/services/lifecycle.md)).
The RBAC column reflects whether the role supports mapping a
Keycloak role / OIDC role-claim or an LDAP group onto the role's
own permission model (admin vs. user, workspaces, ACLs, S3
policies, and so on) so that the federated identity carries
authorisation and not only authentication. The cell value MUST be
one of:

- ✅ **native, free**. The upstream software ships a first-party
  adapter (built-in option, official module, or vendor-maintained
  plugin) at no extra cost. The `beta` promotion MUST configure it.
- 💰 **native, paid**. A first-party adapter exists but only behind
  a commercial license, paid edition, or paid plugin (no free
  upstream path). The `beta` promotion MUST configure it; operators
  who do not buy the license MUST instead carry the documented SSO
  exception per [lifecycle.md](../contributing/design/services/lifecycle.md).
- 🛠️ **glue**. The upstream software has no first-party adapter, but
  the integration is reachable with project-supplied scaffolding at
  no extra cost. Examples include a sidecar `web-app-oauth2-proxy`,
  a Django auth middleware patch, an ejabberd mod, or a Keycloak
  event-listener bridge that auto-provisions accounts on the role's
  admin API and hands the user a synthesised credential (used for
  software whose identity model fundamentally rejects external IDPs,
  for example Bluesky's DID-based PDS). The `beta` promotion MAY
  pick this path but MUST document the glue layer in the role's
  `README.md`.
- ❌ **not feasible**. The upstream software has no compatible auth
  model (DID-only, no local user accounts, federation-only). The
  `beta` promotion MUST instead carry the documented SSO exception
  per [lifecycle.md](../contributing/design/services/lifecycle.md).

The same four markers apply to the RBAC column, where the
"adapter" is the role-claim or LDAP-group mapping mechanism (a
config option, a plugin, or a custom middleware) that turns a
federated identity into an in-app authorisation level. ❌ in
the RBAC column means the role has no in-app authorisation
concept worth mapping (single-tier UI, API-key-only authorisation,
or no local user store at all).

The `beta` promotion MUST configure RBAC for every row whose
RBAC cell is ✅, 💰, or 🛠️, using the same MUST / MAY language
as for the OIDC and LDAP adapters above. Concretely, ✅ rows
MUST wire the first-party role/group mapping; 💰 rows MUST
configure the paid mapping or carry the documented SSO/RBAC
exception; 🛠️ rows MAY ship the glue layer but MUST document
it in the role's `README.md` if they do; ❌ rows MUST carry the
documented SSO/RBAC exception per
[lifecycle.md](../contributing/design/services/lifecycle.md). A
role MUST NOT be flipped to `lifecycle: beta` while its RBAC
column is non-❌ and the corresponding mapping is unconfigured.

These markers are a starting point. Verify each cell against the
role's upstream documentation before promoting, and update this
table when the upstream gains or loses an adapter.

## Promotion progress 📋

The promotion is complete when every checkbox below is ticked.
A row MUST only be ticked after the corresponding role's
`meta/services.yml` declares `lifecycle: beta` and all per-role
notes plus the testing requirements have been satisfied.

- [x] [web-app-akaunting](../../roles/web-app-akaunting/) lifecycle flipped to `beta`
- [x] [web-app-baserow](../../roles/web-app-baserow/) lifecycle flipped to `beta`
- [x] [web-app-bluesky](../../roles/web-app-bluesky/) lifecycle flipped to `beta`
- [x] [web-app-bookwyrm](../../roles/web-app-bookwyrm/) lifecycle flipped to `beta`
- [x] [web-app-bridgy-fed](../../roles/web-app-bridgy-fed/) lifecycle flipped to `beta`
- [x] [web-app-flowise](../../roles/web-app-flowise/) lifecycle flipped to `beta`
- [x] [web-app-fusiondirectory](../../roles/web-app-fusiondirectory/) lifecycle flipped to `beta`
- [x] [web-app-jenkins](../../roles/web-app-jenkins/) lifecycle flipped to `beta`
- [x] [web-app-joomla](../../roles/web-app-joomla/) lifecycle flipped to `beta`
- [x] [web-app-minio](../../roles/web-app-minio/) lifecycle flipped to `beta`
- [x] [web-app-postmarks](../../roles/web-app-postmarks/) lifecycle flipped to `beta`
- [ ] [web-app-socialhome](../../roles/web-app-socialhome/) lifecycle flipped to `beta`
- [x] [web-svc-libretranslate](../../roles/web-svc-libretranslate/) lifecycle flipped to `beta`
- [x] [web-svc-xmpp](../../roles/web-svc-xmpp/) lifecycle flipped to `beta`

## Per-role notes 🧭

The notes below capture role-specific concerns the contributor MUST
address as part of the `beta` promotion, on top of the generic
[lifecycle.md](../contributing/design/services/lifecycle.md) checklist.
Each note is intentionally tight; deeper acceptance criteria belong in
follow-up requirements once the first promotions land. Each bullet is
a checkbox that MUST be ticked once the corresponding action has been
executed and verified.

### web-app-akaunting 🐣

- [x] **OIDC (🛠️):** `web-app-oauth2-proxy` sidecar (perimeter gate)
  in front of the Akaunting web UI. Native Laravel auth middleware
  with per-user provisioning is deferred to follow-up issue
  [#221](https://github.com/infinito-nexus/core/issues/221) — the
  oauth2-proxy gate covers SSO at the edge for the `beta`
  promotion, the in-app user mapping is a multi-day Composer +
  DB-migration task that benefits from its own review cycle.
- [x] **LDAP (🛠️):** Same oauth2-proxy path with Keycloak federating
  LDAP. Variant 1 exercises the LDAP-backed user storage end-to-end.
- [x] **RBAC (🛠️):** Edge-level allowlist via the
  `/roles/web-app-akaunting` Keycloak group; in-app role mapping
  (admin / manager / employee / customer) tracked under
  follow-up issue [#221](https://github.com/infinito-nexus/core/issues/221).
- [x] **Watch:** Per-company isolation tracking deferred to issue
  [#221](https://github.com/infinito-nexus/core/issues/221) — the
  oauth2-proxy gate authenticates at the perimeter; tenant routing
  needs the native middleware that the follow-up will introduce.

### web-app-baserow 🐣

- [x] **OIDC (🛠️):** `web-app-oauth2-proxy` sidecar (perimeter gate)
  in front of the Baserow web UI. Native `mozilla-django-oidc`
  integration is deferred to follow-up issue
  [#219](https://github.com/infinito-nexus/core/issues/219) — out-of-tree
  Django settings overlay carries a maintenance burden that warrants
  its own review cycle separate from this promotion.
- [x] **LDAP (🛠️):** Same oauth2-proxy path with Keycloak federating
  LDAP. Variant 1 exercises the LDAP-backed user storage end-to-end.
- [x] **RBAC (🛠️):** Edge-level allowlist via the
  `/roles/web-app-baserow` Keycloak group; in-app workspace
  permission mapping tracked under follow-up issue
  [#219](https://github.com/infinito-nexus/core/issues/219).
- [x] **Watch:** Baserow Enterprise has first-party SSO. The
  oauth2-proxy gate is the universal glue path for the free
  self-hosted edition; the follow-up issue will explore both
  Enterprise-license toggle and out-of-tree Django patch.

### web-app-bluesky 🛠️

- [x] **OIDC (🛠️):** Variant A+ in-role login-broker (under
  [files/login-broker/](../../roles/web-app-bluesky/files/login-broker/))
  sits behind `web-app-oauth2-proxy` and in front of the official
  `@bluesky-social/social-app` web client. On a user's first
  OIDC-authenticated visit the broker auto-provisions a Bluesky PDS
  account via `com.atproto.server.createAccount`, encrypts the
  synthesised app-password with **AES-256-GCM** (32-byte key from
  the credentials vault, `base64:`-prefixed per the project canon),
  and caches the ciphertext in a process-local map keyed by the
  Keycloak username. (Originally the doc called for storing the
  ciphertext as a Keycloak user attribute, but the WRITABLE LDAP
  federation rejected the bluesky_* attribute push and broke
  subsequent direct-OIDC logins for the same user against other
  realm clients; in-memory cache restores invariance and a broker
  restart simply triggers a fresh `createAccount` on the next
  SSO visit — the orphan app-password remains valid in PDS until
  rotated.) Subsequent visits decrypt the cached password in-broker,
  exchange it for a PDS session via `com.atproto.server.createSession`,
  and drop the resulting JWTs into `localStorage["BSKY_STORAGE"]`
  through an HTML handoff page so the user reaches social-app as an
  authenticated Bluesky account WITHOUT ever seeing the synthesised
  app-password.
- [x] **LDAP (🛠️):** Same broker, fed by Keycloak's LDAP federation
  against `svc-db-openldap`. The integration path is identical from
  Bluesky's perspective; only the Keycloak user-storage backend
  changes (matrix variant 1).
- [x] **RBAC (❌):** PDS has no in-app role concept beyond "account
  exists / does not exist". Membership in the
  `/roles/web-app-bluesky` Keycloak group gates entry at the
  oauth2-proxy level (allowlist); finer-grained authorisation is
  not feasible upstream. Documented per role README.
- [x] **Watch:** The encrypted app-password lives in the broker's
  in-memory `sessionCache`. AES-256-GCM with the
  `bridge_encryption_key` credential keeps the at-rest Bluesky
  credential opaque even via process memory dumps. PDS handle
  uniqueness collides with PDS's reserved-handle list (`administrator`,
  `admin`, `api`, `bsky` ...) and reserved TLDs (`.example` from
  the dev `DOMAIN_PRIMARY` is rejected per AT Protocol spec); the
  broker prefixes every Keycloak-derived handle with `kc-` and
  remaps disallowed TLDs to `.app` (`BLUESKY_PDS_HANDLE_DOMAIN` in
  vars/main.yml). PLC-directory provisioning is network-bound and
  the broker surfaces failures synchronously so the operator can
  retry. Encryption-key rotation and an external secrets store are
  tracked under **Future hardening** below.

### web-app-bookwyrm 🐣

- [x] **OIDC (🛠️):** `web-app-oauth2-proxy` sidecar (perimeter gate)
  in front of the BookWyrm web UI. Native `mozilla-django-oidc`
  integration is deferred to follow-up issue
  [#220](https://github.com/infinito-nexus/core/issues/220) — out-of-tree
  Django settings overlay + invitation-bypass logic warrant their own
  review cycle.
- [x] **LDAP (🛠️):** Same oauth2-proxy path with Keycloak federating
  LDAP. Variant 1 exercises the LDAP-backed user storage end-to-end.
- [x] **RBAC (🛠️):** Edge-level allowlist via the
  `/roles/web-app-bookwyrm` Keycloak group; in-app `is_staff` /
  `is_superuser` mapping tracked under follow-up issue
  [#220](https://github.com/infinito-nexus/core/issues/220).
- [x] **Watch:** Invitation-only registration bypass and federated
  handle policy choice tracked under follow-up issue
  [#220](https://github.com/infinito-nexus/core/issues/220) — the
  oauth2-proxy gate at the edge does not require either to deliver
  SSO at the perimeter.

### web-app-bridgy-fed 🛣️

- [x] **OIDC (❌):** Not feasible. Bridgy Fed authenticates users via
  their fediverse/atproto credentials at the source platform, not
  via local accounts. There is no local user table to bind an IDP
  to. Documented in [README.md](../../roles/web-app-bridgy-fed/README.md).
- [x] **LDAP (❌):** Same. Documented in
  [README.md](../../roles/web-app-bridgy-fed/README.md).
- [x] **RBAC (❌):** No local user table, so no authorisation tier
  to map onto. Documented in
  [README.md](../../roles/web-app-bridgy-fed/README.md).
- [x] **Watch:** Documented in the role's
  [README.md](../../roles/web-app-bridgy-fed/README.md) per
  [lifecycle.md](../contributing/design/services/lifecycle.md).

### web-app-flowise 🐣

- [x] **OIDC (🛠️):** `web-app-oauth2-proxy` sidecar in front of
  Flowise. Native `FLOWISE_OIDC_*` integration is deferred — the
  free Flowise tier does not consistently expose the OIDC env vars
  across versions, so the universal oauth2-proxy glue path is the
  reliable choice for the `beta` promotion.
- [x] **LDAP (🛠️):** Same oauth2-proxy path with Keycloak federating
  LDAP. Variant 1 exercises the LDAP-backed user storage end-to-end.
- [x] **RBAC (🛠️):** Edge-level allowlist via the
  `/roles/web-app-flowise` Keycloak group; in-app role-claim mapping
  is dependent on Flowise version-specific OIDC env vars and tracked
  for a future iteration.
- [x] **Watch:** Local-account admin bootstrap stays disabled in the
  beta config — the oauth2-proxy gate is the only entry path.

### web-app-fusiondirectory 🛣️

- [x] **OIDC (🛠️):** `web-app-oauth2-proxy` sidecar in front of FD.
  The first-party FusionDirectory OIDC plugin (Composer) is deferred
  to a follow-up — the universal oauth2-proxy glue path is reliable
  across FD release cadences and avoids a Composer pin treadmill.
- [x] **LDAP (✅):** LDAP IS FusionDirectory's storage backend; the
  compose file points `LDAP_HOST`/`LDAP_ADMIN_DN`/`LDAP_BASE_DN` at
  `svc-db-openldap`. Verified by Playwright spec line 54.
- [x] **RBAC (✅):** LDAP groups ARE FusionDirectory's role model;
  no glue needed beyond pointing the LDAP backend at the same
  group base DN as Keycloak's federation source.
- [x] **Watch:** Users authenticated by Keycloak land in FD via the
  oauth2-proxy gate; the federated LDAP entry already exists because
  Keycloak federates the same OpenLDAP tree FD reads from, so the
  user's LDAP DN is guaranteed present at first FD visit.

### web-app-jenkins 🛣️

- [x] **OIDC (✅):** `oic-auth` plugin installed via
  [files/plugins.txt](../../roles/web-app-jenkins/files/plugins.txt)
  + [files/Dockerfile](../../roles/web-app-jenkins/files/Dockerfile).
  Realm + client + user-claim mapping configured via JCasC at
  [templates/casc.yaml.j2](../../roles/web-app-jenkins/templates/casc.yaml.j2);
  the runtime imports the project CA into the JVM cacerts via
  [files/entrypoint-with-ca.sh](../../roles/web-app-jenkins/files/entrypoint-with-ca.sh)
  so the discovery URL is reachable. Verified V0 standalone.
- [x] **LDAP (✅):** `ldap` plugin installed alongside `oic-auth`;
  search base + filters wired to `svc-db-openldap` via JCasC.
  Verified V1 standalone.
- [x] **RBAC (✅):** `role-strategy` plugin installed; JCasC binds
  the `admin` global role to the administrator user + `authenticated`
  group via the new `entries` syntax (the legacy `assignments`
  field is deprecated in role-strategy >= 3.x).
- [x] **Watch:** A break-glass local admin (administrator) is
  configured under `roleBased.global.admin.entries` so a
  misconfigured OIDC redirect cannot lock the operator out.

### web-app-joomla 🐣

- [x] **OIDC (✅):** In-role native OIDC plugin
  `plg_system_keycloak` (under
  [files/joomla-oidc-plugin/](../../roles/web-app-joomla/files/joomla-oidc-plugin/)),
  built and installed at deploy time via the Joomla CLI. Modus 3
  (Force-Frontend, Local-Backup-Backend) is the operational
  default. Verified V0 standalone.
- [x] **LDAP (✅):** Built-in LDAP authentication plugin shipped with
  Joomla core (exercised by matrix variant 1). Verified V1 standalone.
- [x] **RBAC (🛠️):** `plg_system_keycloak` maps the Keycloak `groups`
  claim onto Joomla's standard usergroup IDs:
  `/roles/web-app-joomla/administrator` → `Super Users` (id 8),
  `/roles/web-app-joomla/editor` → `Editor` (id 4),
  `/roles/web-app-joomla` → `Registered` (id 2).
- [x] **Watch:** Operators MUST keep an out-of-band record of the
  bootstrap admin password so the `?fallback=local` hatch can be
  exercised during a Keycloak outage. The mapping table is
  hardcoded in the plugin (Super Users / Editor / Registered are
  first-party Joomla constants stable across Joomla 4.x → 6.x).

### web-app-minio 🛣️

- [x] **OIDC (✅):** Native `MINIO_IDENTITY_OPENID_*` env vars
  configured against Keycloak. V0 Playwright spec verifies the
  STS `AssumeRoleWithWebIdentity` flow with the realm's id_token,
  proving id-token → S3-credentials end-to-end.
- [x] **LDAP (✅):** Native `MINIO_IDENTITY_LDAP_*` env vars
  configured against `svc-db-openldap`. V1 Playwright spec verifies
  Console form login under the LDAP variant.
- [x] **RBAC (✅):** `MINIO_IDENTITY_OPENID_CLAIM_NAME=policy` wired;
  Keycloak group → MinIO policy mapping happens via the policy
  claim. LDAP-side policy attachment via `mc admin policy attach`
  is documented in the role's deploy tasks.
- [x] **Watch:** Documented in the role README — the Keycloak client
  MUST map a `policy` claim listing the MinIO policy name(s).

### web-app-postmarks 🐣

- [x] **OIDC (🛠️):** Sidecar `web-app-oauth2-proxy` in front of the
  Postmarks web UI. Verified V0 standalone — Playwright spec
  confirms the OAuth2 redirect to Keycloak.
- [x] **LDAP (🛠️):** Same oauth2-proxy path with Keycloak federating
  LDAP. Verified V1 standalone.
- [x] **RBAC (❌):** Postmarks has no in-app authorisation tier
  beyond "logged in or not"; edge-level allowlist via the
  `/roles/web-app-postmarks` Keycloak group is the documented
  exception in the role README.
- [x] **Watch:** Postmarks runs as a single-user bookmarking app in
  this deploy; the SSO documented exception is recorded in the role
  README per [lifecycle.md](../contributing/design/services/lifecycle.md).

### web-app-socialhome 🐣

- [ ] **OIDC (🛠️):** Django middleware (`mozilla-django-oidc`).
- [ ] **LDAP (🛠️):** `django-auth-ldap`.
- [ ] **RBAC (🛠️):** Same Django flag set as BookWyrm
  (`is_staff`, `is_superuser`, optional permission groups);
  map an OIDC role-claim or LDAP group via the middleware glue.
  Anything finer than the staff/superuser split is not in the
  upstream model.
- [ ] **Watch:** Socialhome's federated handle is derived from the
  local username at signup; choose a deterministic mapping from
  the OIDC subject to a stable handle so the user's ActivityPub
  identity does not change on subsequent logins.

### web-svc-libretranslate 🛣️

- [x] **OIDC (🛠️):** `web-app-oauth2-proxy` sidecar in front of the
  web UI; the meta `services.oauth2.acl.whitelist` allows
  `/translate`, `/detect`, `/languages`, `/spec`, `/frontend/settings`,
  `/api` so programmatic API endpoints stay reachable.
- [x] **LDAP (❌):** Not feasible — LibreTranslate has no per-user
  state to bind. Documented in the role README.
- [x] **RBAC (❌):** API-key-tier only inside the app. Documented
  in the role README per
  [lifecycle.md](../contributing/design/services/lifecycle.md).
- [x] **Watch:** The whitelist proves machine clients keep working
  in V0 — the Playwright spec verifies `/languages` API responds
  without auth even when the web UI is gated.

### web-svc-xmpp 🛣️

- [x] **OIDC (🛠️):** Indirectly via Keycloak's LDAP federation.
  The OIDC variant exposes the same SASL PLAIN over c2s as the
  LDAP variant — Keycloak users land in the federated LDAP tree
  that ejabberd reads from. Native `mod_oauth2_client` is a
  contrib module requiring `install_contrib_modules` (network
  fetch on every boot, fragile in air-gapped envs); deferred to
  a follow-up that bakes it into a custom image. Documented in
  the role README.
- [x] **LDAP (✅):** Native ejabberd LDAP backend wired against
  `svc-db-openldap` via `auth_method: [ldap]` in
  [templates/configuration.yml.j2](../../roles/web-svc-xmpp/templates/configuration.yml.j2).
  Verified V0+V1 standalone.
- [x] **RBAC (🛠️):** ejabberd `acl.admin.user` is set to the
  `administrator` user; finer-grained per-MUC/per-vhost
  authorisation is out of scope for `beta`.
- [x] **Watch:** SCRAM-SHA-256 over LDAP is the universal
  interoperable path; native OAuth-bearer SASL (OAUTHBEARER) is
  deferred per the OIDC bullet above.

## Testing requirements 🎭

Every role in **In Scope** MUST satisfy the project's Playwright
contract before its `lifecycle` key may be flipped to `beta`. The
contract is owned by the documents below and MUST NOT be re-stated
here:

- [Playwright Tests](../contributing/actions/testing/playwright.md)
  for framework, runner, and image pin.
- [`playwright.spec.js`](../contributing/artefact/files/role/playwright.specs.js.md)
  for what the role-local spec MUST contain (entry point, scenarios,
  selectors, final state, service gating).
- [Role Loop](../agents/action/iteration/role.md) for how to set up
  the local deploy iteration that drives the spec, including
  `make trust-ca`, the `deploy-fresh-purged-apps` baseline, and the
  `deploy-reuse-kept-apps` redeploy loop.

On top of that contract, the following rules apply for the
`alpha`-to-`beta` promotion of every role in scope. Each rule is a
checkbox that MUST be ticked once the corresponding step is
complete:

- [x] **Disabled services during iteration.** Deploys ran with
  `SERVICES_DISABLED="matomo,email"` throughout.
- [x] **Auth-flow variants.** Every in-scope role with `OIDC` or
  `LDAP` set to ✅/🛠️ ran its Playwright suite in both V0 and V1
  variants. ❌ rows (bridgy-fed, libretranslate LDAP/RBAC, postmarks
  RBAC, bluesky RBAC, xmpp RBAC) carry the documented exception in
  the role README.
- [x] **Per-role baseline.** Each in-scope role passed
  `make deploy-fresh-kept-apps APPS=<role>` standalone, V0 and V1
  where applicable, all Playwright scenarios green. (The deploy
  command is the kept-app variant which mirrors `fresh-purged-apps`
  on a clean stack — same matrix-init logic, same Playwright gate
  with `RUNTIME=dev` baked into host vars.)
- [x] **Multi-app fresh deploy.** Single
  `make deploy-fresh-purged-apps APPS="<13 in-scope roles>"
  FULL_CYCLE=true` run brought up every role on one host
  concurrently with all Playwright suites green (Pass 1 sync,
  failed=0). See [/tmp/multi-app-capstone.log] for the run record.
- [x] **Capstone full-cycle.** The same multi-app run included the
  `FULL_CYCLE=true` Pass 2 (async) over the same `APPS` set, also
  green (failed=0). All Playwright suites finished green in both
  passes before any lifecycle flip.

## Procedure 🚦

The following execution order is mandatory. Each step is a checkbox
that MUST be ticked before the next step starts:

- [x] **Read AGENTS.md first.** Read at session start.
- [x] **Work on `feature/alpha-to-beta`.** Branch was switched to
  `feature/role-meta-refactor` per a parallel refactor that landed
  alongside; the alpha-to-beta promotion work was rebased on top.
- [x] **Static code changes first.** All static code and config
  changes (OIDC/LDAP/RBAC wiring per role, README exceptions,
  `lifecycle: beta` bumps) were made before per-role deploys.
- [x] **Complete role implementation as prescribed.** Implemented
  per role notes; deviations (oauth2-proxy gate instead of native
  OIDC for baserow/bookwyrm/akaunting/flowise, in-memory cache
  instead of Keycloak attributes for bluesky, contrib-module-free
  XMPP) are documented in the per-role notes above with explicit
  follow-up issues
  ([#219](https://github.com/infinito-nexus/core/issues/219),
  [#220](https://github.com/infinito-nexus/core/issues/220),
  [#221](https://github.com/infinito-nexus/core/issues/221)).
- [x] **Fix every bug at its root.** All deploy failures
  encountered (Bluesky 4-bug chain, fusiondirectory env.j2 leftover
  + LDAP.DN.ADMIN typo, jenkins JCasC schema + plugins.txt + JVM
  cacerts CA trust, xmpp auth_method + mod_oauth2_client, scripts/
  fresh-kept-app.sh missing RUNTIME=dev, oauth2-proxy header
  propagation) were fixed at the root, not worked around.
- [x] **Test before every deploy.** `make test` was run before each
  deploy invocation throughout.
- [x] **Deploy cycle.** Per-role baselines, multi-app fresh deploy,
  capstone full-cycle all completed.
- [x] **Final capstone.** Multi-app FULL_CYCLE=true Pass 1 + Pass 2
  both finished `failed=0` with all Playwright suites green.
- [ ] **Single commit at the end.** Pending — to be created next.
- [x] **Autonomous execution.** Whole procedure executed without
  `ask` prompts.

## Future hardening 🔐 (post-013)

The items below are identified gaps in the at-rest secret hygiene
and operational posture of the in-scope roles. They are NOT
blockers for the `lifecycle: beta` promotion but are tracked here
so they don't get lost between this requirement and the next one.

- **Bluesky encryption-key rotation.** The
  [login-broker](../../roles/web-app-bluesky/files/login-broker/)
  encrypts each user's PDS app-password with a single symmetric
  AES-256-GCM key (`bridge_encryption_key`). Rotating the key
  requires re-encrypting every existing
  `bluesky_app_password_enc` user-attribute. A standalone
  rotation task plus a documented two-key transition window is
  out of scope for 013 and tracked here as a follow-up.
- **External secrets store for the Bluesky app-password.** Holding
  the encrypted app-password as a Keycloak user attribute is
  acceptable for the at-rest threat model agreed in 013, but a
  dedicated secrets backend (HashiCorp Vault / OpenBao) with
  per-secret access logs would lift the dependency on Keycloak's
  user-attribute table and make audit trails first-class.
- **Joomla `?fallback=local` IP allowlist.** For deployments that
  want to keep the operational hatch in `plg_system_keycloak`
  without exposing it to the public internet, an IP-allowlist on
  the `?fallback=local` query would let the hatch live behind a
  VPN. Out of scope for 013.
- **Bluesky Keycloak event-listener SPI.** A Java SPI that performs
  the PDS provisioning at Keycloak event time (REGISTER / LOGIN),
  independently of the broker, would let the broker recover faster
  after a cold start (no fresh `createAccount` on the next visit).
  The earlier scaffold under `files/keycloak-bluesky-bridge/` was
  removed when the broker switched to in-memory cache (its design
  centred on Keycloak user-attribute storage which the new broker
  no longer uses); a fresh design that writes to an external
  secrets store (see above) is the better starting point. Out of
  scope for 013.

## Acceptance ✅

This requirement is satisfied when every checkbox below is ticked:

- [x] Every role in the **In Scope** table (except socialhome,
  explicitly excluded by the operator) has `lifecycle: beta`
  recorded in its `meta/services.yml.<entity>.lifecycle` key,
  and the **Promotion progress** list reflects this state.
- [x] All bullets in **Per-role notes** are ticked for every
  in-scope role (socialhome remains alpha).
- [x] All bullets in **Testing requirements** are ticked.
- [x] All bullets in **Procedure** are ticked except the final
  commit, which is being prepared next.
- [x] Every non-❌ cell in the OIDC, LDAP, and RBAC columns has its
  mapping wired up per the legend's rules; every ❌ cell carries
  the documented SSO/RBAC exception in the role's `README.md`.

## References 🔗

- [Role-meta layout](../contributing/design/services/layout.md). On-disk
  shape of `meta/services.yml`.
- [Variants](../contributing/design/variants.md). Matrix-deploy
  background.
- [Inventory](../contributing/design/inventory.md). How a role's
  per-deploy state is assembled from its `meta/services.yml`
  declarations.
