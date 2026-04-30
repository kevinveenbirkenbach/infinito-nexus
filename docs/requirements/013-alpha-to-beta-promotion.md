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

- [ ] [web-app-akaunting](../../roles/web-app-akaunting/) lifecycle flipped to `beta`
- [ ] [web-app-baserow](../../roles/web-app-baserow/) lifecycle flipped to `beta`
- [ ] [web-app-bluesky](../../roles/web-app-bluesky/) lifecycle flipped to `beta`
- [ ] [web-app-bookwyrm](../../roles/web-app-bookwyrm/) lifecycle flipped to `beta`
- [ ] [web-app-bridgy-fed](../../roles/web-app-bridgy-fed/) lifecycle flipped to `beta`
- [ ] [web-app-flowise](../../roles/web-app-flowise/) lifecycle flipped to `beta`
- [ ] [web-app-fusiondirectory](../../roles/web-app-fusiondirectory/) lifecycle flipped to `beta`
- [ ] [web-app-jenkins](../../roles/web-app-jenkins/) lifecycle flipped to `beta`
- [ ] [web-app-joomla](../../roles/web-app-joomla/) lifecycle flipped to `beta`
- [ ] [web-app-minio](../../roles/web-app-minio/) lifecycle flipped to `beta`
- [ ] [web-app-postmarks](../../roles/web-app-postmarks/) lifecycle flipped to `beta`
- [ ] [web-app-socialhome](../../roles/web-app-socialhome/) lifecycle flipped to `beta`
- [ ] [web-svc-libretranslate](../../roles/web-svc-libretranslate/) lifecycle flipped to `beta`
- [ ] [web-svc-xmpp](../../roles/web-svc-xmpp/) lifecycle flipped to `beta`

## Per-role notes 🧭

The notes below capture role-specific concerns the contributor MUST
address as part of the `beta` promotion, on top of the generic
[lifecycle.md](../contributing/design/services/lifecycle.md) checklist.
Each note is intentionally tight; deeper acceptance criteria belong in
follow-up requirements once the first promotions land. Each bullet is
a checkbox that MUST be ticked once the corresponding action has been
executed and verified.

### web-app-akaunting 🐣

- [ ] **OIDC (🛠️):** Custom Laravel auth middleware that consumes
  `X-Forwarded-User` from a sidecar `web-app-oauth2-proxy`, plus
  Akaunting's `auth.php` extended to short-circuit the local
  email/password form. Map the OIDC subject to Akaunting's `users`
  table by email.
- [ ] **LDAP (🛠️):** `Adldap2/Adldap2-Laravel`-style integration or the
  same oauth2-proxy path with an LDAP backend.
- [ ] **RBAC (🛠️):** Map an OIDC role-claim or LDAP group onto
  Akaunting's `roles` / `user_roles` pivot (admin / manager /
  employee / customer) inside the same middleware that creates
  the user.
- [ ] **Watch:** Akaunting's per-company isolation. Each user is scoped
  to one or more companies via `user_companies`; the SSO bridge
  MUST assign a default company on first login, otherwise the user
  lands on a blank dashboard.

### web-app-baserow 🐣

- [ ] **OIDC (🛠️):** `mozilla-django-oidc`. Map the OIDC subject to
  Baserow's `User` model by email; configure a default
  workspace/group on first login.
- [ ] **LDAP (🛠️):** `django-auth-ldap`. Group mapping to Baserow
  workspace permissions needs explicit configuration.
- [ ] **RBAC (🛠️):** Use mozilla-django-oidc's `claims_to_user`
  hook (or django-auth-ldap's `AUTH_LDAP_USER_FLAGS_BY_GROUP` /
  group lookup) to translate an OIDC role-claim or LDAP group
  into Baserow's workspace permission level (admin, builder,
  editor, viewer, commenter).
- [ ] **Watch:** Baserow Enterprise ships its own SSO. The 🛠️ path is
  for the free self-hosted edition; do NOT mix Enterprise auth and
  the glue path in the same deploy.

### web-app-bluesky 🛠️

- [ ] **OIDC (🛠️):** Keycloak event-listener bridge to PDS
  `com.atproto.server.createAccount` that stores the synthesised
  app-password as a Keycloak user attribute. Surface that password
  in the user's self-service portal so the user can paste it into
  the official Bluesky web/app client.
- [ ] **LDAP (🛠️):** Same bridge, fed by Keycloak's LDAP federation
  against `svc-db-openldap`. Do NOT attempt direct LDAP-to-PDS
  sync; Keycloak's federation layer is the single source of truth.
- [ ] **RBAC (❌):** PDS has no in-app role concept beyond "account
  exists / does not exist". Document the SSO/RBAC exception per
  [lifecycle.md](../contributing/design/services/lifecycle.md).
- [ ] **Watch:** PDS handle uniqueness collides with Keycloak's username
  freedoms (dots, plus signs). The bridge MUST sanitise handles to
  the AT Protocol's allowed character set and surface the sanitised
  handle back to the user. The PLC-directory dependency also makes
  the initial provisioning network-bound; budget retries.

### web-app-bookwyrm 🐣

- [ ] **OIDC (🛠️):** Django middleware (`mozilla-django-oidc`).
- [ ] **LDAP (🛠️):** `django-auth-ldap`.
- [ ] **RBAC (🛠️):** BookWyrm only exposes Django's `is_staff` /
  `is_superuser` flags plus a small set of permission groups.
  Map an OIDC role-claim or LDAP group to those flags via the
  middleware glue; finer-grained roles do not exist upstream.
- [ ] **Watch:** BookWyrm uses invitation-only registration by default;
  the SSO-driven user creation MUST bypass or pre-create an invite
  for the first login. The user's ActivityPub actor URL is also
  pinned to the local username at creation time; choose the
  username derivation policy explicitly.

### web-app-bridgy-fed 🛣️

- [ ] **OIDC (❌):** Not feasible. Bridgy Fed authenticates users via
  their fediverse/atproto credentials at the source platform, not
  via local accounts. There is no local user table to bind an IDP
  to.
- [ ] **LDAP (❌):** Same.
- [ ] **RBAC (❌):** No local user table, so no authorisation tier
  to map onto.
- [ ] **Watch:** Document the exception explicitly in the role's
  `README.md` per [lifecycle.md](../contributing/design/services/lifecycle.md).
  Operators MUST understand that placing Bridgy Fed behind
  oauth2-proxy would break inbound federation traffic.

### web-app-flowise 🐣

- [ ] **OIDC (✅):** Built-in via `FLOWISE_OIDC_*` environment
  variables. Configure realm, client ID/secret, and the scope
  list. Pin a Flowise version that exposes the variables you
  depend on (see Watch).
- [ ] **LDAP (🛠️):** No first-party LDAP; oauth2-proxy with LDAP
  backend.
- [ ] **RBAC (🛠️):** Flowise can map an OIDC role-claim onto its
  workspace/permission model via the same `FLOWISE_OIDC_*`
  config; the LDAP path needs an oauth2-proxy claim layer to
  forward role headers. Pin the Flowise version that supports
  the role-claim mapping you configure.
- [ ] **Watch:** Disable the local-account `FLOWISE_USERNAME` /
  `FLOWISE_PASSWORD` admin bootstrap when SSO is active to avoid
  a parallel un-federated admin path.

### web-app-fusiondirectory 🛣️

- [ ] **OIDC (✅):** First-party OIDC plugin (FusionDirectory has a
  pluggable auth layer). Install via Composer.
- [ ] **LDAP (✅):** LDAP IS FusionDirectory's storage backend; point
  it at `svc-db-openldap`.
- [ ] **RBAC (✅):** LDAP groups ARE FusionDirectory's role model;
  the OIDC plugin re-uses the same group lookup. No glue is
  needed beyond pointing both adapters at the same group base
  DN.
- [ ] **Watch:** FusionDirectory's OIDC plugin pulls in Composer
  dependencies; pin a known-good version per its release notes.
  When users land in FD via OIDC, ensure their LDAP DN already
  exists (the LDAP federation in Keycloak handles this when wired
  correctly).

### web-app-jenkins 🛣️

- [ ] **OIDC (✅):** Install the `oic-auth` plugin. Configure realm,
  client, and the user-claim mapping.
- [ ] **LDAP (✅):** Install the `ldap` plugin. Configure search
  base, user filter, and group filter.
- [ ] **RBAC (✅):** Install `role-strategy` (or `matrix-auth`) and
  bind Jenkins authorities to OIDC role-claims and LDAP groups.
  Both `oic-auth` and the `ldap` plugin expose group lookup that
  feeds the strategy plugin natively.
- [ ] **Watch:** Keep a break-glass local admin account valid through
  plugin install/upgrade so a misconfigured OIDC plugin does not
  lock everyone out. The initial-setup admin token has a short
  validity window; capture it before it expires.

### web-app-joomla 🐣

- [ ] **OIDC (✅):** In-role native OIDC plugin
  `plg_system_keycloak` (under
  [files/joomla-oidc-plugin/](../../roles/web-app-joomla/files/joomla-oidc-plugin/)),
  built and installed at deploy time via the Joomla CLI. Modus 3
  (Force-Frontend, Local-Backup-Backend) is the operational
  default: every visit to `/` and `/administrator` redirects to
  Keycloak unless the request explicitly carries `?fallback=local`
  AND the env-var `JOOMLA_OIDC_FALLBACK_ENABLED` is `true`. The
  fallback hatch is env-toggleable so high-security deployments can
  flip to Modus 1 (no local form, IdP is the only path).
- [ ] **LDAP (✅):** Built-in LDAP authentication plugin shipped with
  Joomla core (exercised by matrix variant 1).
- [ ] **RBAC (🛠️):** `plg_system_keycloak` maps the Keycloak `groups`
  claim onto Joomla's standard usergroup IDs:
  `/roles/web-app-joomla/administrator` → `Super Users` (id 8),
  `/roles/web-app-joomla/editor` → `Editor` (id 4),
  `/roles/web-app-joomla` → `Registered` (id 2). A user whose
  Keycloak groups match none of these paths is refused; this is
  the documented RBAC gate.
- [ ] **Watch:** Operators MUST keep an out-of-band record of the
  bootstrap admin password so the `?fallback=local` hatch can be
  exercised during a Keycloak outage; the alternative is locking
  the IdP itself out of the rescue path. The mapping table above
  is intentionally hardcoded in the plugin to keep the role-meta
  layer free of Joomla-internal IDs (Super Users / Editor /
  Registered are first-party Joomla constants and stable across
  Joomla 4.x → 6.x).

### web-app-minio 🛣️

- [ ] **OIDC (✅):** Set `MINIO_IDENTITY_OPENID_CONFIG_URL`,
  `MINIO_IDENTITY_OPENID_CLIENT_ID`,
  `MINIO_IDENTITY_OPENID_CLIENT_SECRET`,
  `MINIO_IDENTITY_OPENID_CLAIM_NAME` (typically `policy`), and
  `MINIO_IDENTITY_OPENID_SCOPES`.
- [ ] **LDAP (✅):** Set `MINIO_IDENTITY_LDAP_*` env vars; configure
  the user/group filters against `svc-db-openldap`.
- [ ] **RBAC (✅):** `MINIO_IDENTITY_OPENID_CLAIM_NAME` (typically
  `policy`) maps a Keycloak claim listing the MinIO policy
  name(s); LDAP-side policy attachment is via group DN to
  policy binding (`mc admin policy attach`). Both paths are
  first-party.
- [ ] **Watch:** MinIO assigns S3 access via policies, NOT roles. The
  Keycloak client MUST map a `policy` claim that lists the MinIO
  policy name; without it, federated users get zero access.

### web-app-postmarks 🐣

- [ ] **OIDC (🛠️):** Sidecar `web-app-oauth2-proxy` in front of the
  Postmarks web UI; map authenticated users by email or sub claim.
- [ ] **LDAP (🛠️):** Same via oauth2-proxy with LDAP backend.
- [ ] **RBAC (❌):** Postmarks has no in-app authorisation tier
  beyond "logged in or not". If multi-tier authorisation is
  needed, gate at the oauth2-proxy level and document the
  exception per
  [lifecycle.md](../contributing/design/services/lifecycle.md).
- [ ] **Watch:** Verify Postmarks actually has multi-user separation
  worth integrating before investing. If the role only ever runs
  single-user, the SSO documented exception per
  [lifecycle.md](../contributing/design/services/lifecycle.md) may
  be the saner outcome.

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

- [ ] **OIDC (🛠️):** Sidecar `web-app-oauth2-proxy` in front of the
  human-facing web UI only.
- [ ] **LDAP (❌):** Not feasible. LibreTranslate authenticates
  programmatic clients with API keys; LDAP cannot map onto that.
- [ ] **RBAC (❌):** Authorisation in LibreTranslate is API-key-tier
  only and decoupled from any IdP. The OIDC/oauth2-proxy gate
  protects the UI but does not grant differential authorisation
  inside the app. Document the exception per
  [lifecycle.md](../contributing/design/services/lifecycle.md).
- [ ] **Watch:** Programmatic API endpoints (`/translate`,
  `/detect`, and so on) MUST stay reachable with API-key auth even
  when the web UI is gated by OIDC; otherwise machine clients
  break. Restrict the OIDC gate to the UI subpath.

### web-svc-xmpp 🛣️

- [ ] **OIDC (✅):** ejabberd `mod_oauth2_client` (or Prosody
  equivalent). Configure realm, client, and the
  XEP-0084-compatible flow.
- [ ] **LDAP (✅):** Native ejabberd LDAP backend (or Prosody's
  `mod_auth_ldap`).
- [ ] **RBAC (🛠️):** ejabberd / Prosody only distinguish "admin"
  from "user" out of the box. Map an LDAP group or OIDC
  role-claim onto the server's admin `acl` list; finer-grained
  authorisation (per-MUC ACL, per-vhost rights) is out of
  scope for the `beta` promotion.
- [ ] **Watch:** Many XMPP clients do not support OAuth-bearer-token
  authentication. LDAP + SCRAM-SHA-256 is the more interoperable
  default. If you advertise OIDC, document the small set of XMPP
  clients confirmed to work (Conversations, Movim, Dino) and keep
  LDAP+SCRAM as the fallback path.

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

- [ ] **Disabled services during iteration.** The deploy MUST run
  with `SERVICES_DISABLED="matomo,email"` per
  [Role Loop](../agents/action/iteration/role.md). The promotion
  gate validates the role itself, not its Matomo or email
  integrations, and skipping those providers cuts iteration time
  and removes a class of unrelated flakes.
- [ ] **Auth-flow variants.** Every role whose **In Scope** row has
  `OIDC` or `LDAP` set to ✅ or 🛠️ MUST run its Playwright suite
  twice, once in an `oidc` variant and once in an `ldap` variant,
  via the [variants.md](../contributing/design/variants.md)
  mechanism. The variant folder MUST configure the relevant
  `services.<oidc|ldap>.enabled` flag, and at least one persona
  scenario MUST take the integrated login path per the
  [`playwright.spec.js`](../contributing/artefact/files/role/playwright.specs.js.md)
  rules. A role that has ❌ in a column MUST document the
  exception in its `README.md` and skip the corresponding
  variant.
- [ ] **Per-role baseline.** Before the multi-app capstone below,
  each role in scope MUST first pass `make deploy-fresh-purged-apps
  APPS=<role> FULL_CYCLE=true` standalone, in BOTH auth-flow
  variants where applicable, with all Playwright scenarios green.
- [ ] **Multi-app fresh deploy.** The promotion MUST include a
  single `make deploy-fresh-purged-apps APPS="<all in-scope
  roles>" FULL_CYCLE=true` run that brings up every role in scope
  on one host concurrently, with `SERVICES_DISABLED="matomo,email"`
  and every role's Playwright suite green. Per-role green is
  necessary but not sufficient; cross-role inventory, port, and
  shared-service collisions only surface at the matrix level.
- [ ] **Capstone full-cycle.** The promotion MUST conclude with one
  full-matrix `FULL_CYCLE=true` pass over the same `APPS` set,
  exercising every variant of every role end-to-end (including the
  `oidc` and `ldap` variants above). All Playwright suites MUST
  finish green in this final run before any role's `lifecycle` key
  is flipped to `beta`.

## Procedure 🚦

The following execution order is mandatory. Each step is a checkbox
that MUST be ticked before the next step starts:

- [ ] **Read AGENTS.md first.** At the start of the session, read
  [AGENTS.md](../../AGENTS.md) and follow all instructions in it
  before any other action. Every subsequent step assumes those
  instructions are in effect.
- [ ] **Work on `feature/alpha-to-beta`.** All changes for this
  requirement MUST land on the `feature/alpha-to-beta` branch.
  Confirm the branch is checked out before any edit; create or
  rebase it onto the current `main` if it is missing or stale.
  Other branches MUST NOT receive promotion work.
- [ ] **Static code changes first.** All static code and
  configuration changes required by **Per-role notes** (OIDC, LDAP,
  and RBAC wiring; SSO/RBAC exception text in the role's
  `README.md`) and the `lifecycle: beta` bumps in each
  `meta/services.yml` MUST be made BEFORE any deploy is started.
  Deploy-driven debugging MUST NOT happen during this phase.
- [ ] **Complete role implementation as prescribed.** Every role in
  scope MUST be implemented in full per its **Per-role notes** (OIDC,
  LDAP, and RBAC wiring plus Watch caveats), the
  [lifecycle.md](../contributing/design/services/lifecycle.md) `beta`
  checklist, and the role's `README.md` rules. Partial
  implementations, skipped configuration items, or "good enough for
  now" cuts MUST NOT be used to satisfy the promotion.
- [ ] **Fix every bug at its root.** Any bug, deploy failure,
  Playwright failure, `make test` failure, runtime error, or
  healthcheck flap encountered during the procedure MUST be fixed
  at its root in this branch before the procedure continues.
  Workarounds, ad-hoc skips, retry-until-green loops, or
  "track in a follow-up" deferrals MUST NOT be used to make a step
  go green.
- [ ] **Test before every deploy.** `make test` MUST pass before
  every `make deploy-*` invocation. A failing `make test` MUST
  block the deploy until the underlying issue is fixed; the
  failure MUST NOT be skipped or ignored.
- [ ] **Deploy cycle.** Once the static changes are in place, run
  the per-role baseline, the multi-app fresh deploy, and the
  capstone full-cycle as described under **Testing requirements**.
- [ ] **Final capstone.** The procedure MUST end with a final
  full-matrix `FULL_CYCLE=true` deploy covering every role in
  scope, with all Playwright suites green.
- [ ] **Single commit at the end.** ALL changes (code, config,
  `README.md` exceptions, lifecycle bumps, and the ticked
  checkboxes in this document) MUST be combined into ONE commit,
  created only after the final capstone has finished green.
  Per-step commits for sub-batches MUST NOT be created.
- [ ] **Autonomous execution.** The whole procedure MUST be
  executed autonomously. No `permissions.ask` prompt MAY be
  triggered until the final commit is being staged. Where a tool
  would otherwise route through `ask`, the procedure MUST select
  an equivalent already covered by `permissions.allow` in
  [.claude/settings.json](../../.claude/settings.json) instead of
  pausing for confirmation.

## Acceptance ✅

This requirement is satisfied when every checkbox below is ticked:

- [ ] Every role in the **In Scope** table has `lifecycle: beta`
  (or a higher tier) recorded in its
  `meta/services.yml.<entity>.lifecycle` key, and the
  **Promotion progress** list reflects this state.
- [ ] All bullets in **Per-role notes** are ticked for every
  in-scope role.
- [ ] All bullets in **Testing requirements** are ticked.
- [ ] All bullets in **Procedure** are ticked.
- [ ] Every non-❌ cell in the OIDC, LDAP, and RBAC columns has its
  mapping wired up per the legend's MUST / MAY rules, and every ❌
  cell carries the documented SSO/RBAC exception in the role's
  `README.md`.

## References 🔗

- [Role-meta layout](../contributing/design/services/layout.md). On-disk
  shape of `meta/services.yml`.
- [Variants](../contributing/design/variants.md). Matrix-deploy
  background.
- [Inventory](../contributing/design/inventory.md). How a role's
  per-deploy state is assembled from its `meta/services.yml`
  declarations.
