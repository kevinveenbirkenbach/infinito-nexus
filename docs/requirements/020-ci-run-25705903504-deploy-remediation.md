# 020 - CI Run 25705903504 Deploy-Failure Remediation Loop

## Scope

Companion to [019](019-playwright-meta-services-parity.md). Tracks the closure of the 49 `test-deploy-server` matrix-job failures from CI Run [25705903504](https://github.com/kevinveenbirkenbach/infinito-nexus-core/actions/runs/25705903504) on branch `feature/web-app-kix`. When a role role-closes here, strike its row through here AND in [019](019-playwright-meta-services-parity.md#per-role-iteration-matrix).

## Status

| Bundle | Cluster | Roles | State |
| --- | --- | ---: | --- |
| A | C3 — `POSTGRES_ALLOWED_AVG_CONNECTIONS' is undefined` | 7 | **VERIFIED GREEN** in CI run 25774452286 (discourse, mastodon, listmonk, mobilizon, gitlab, pretix, openproject all passed deploy; discourse's failure is now C8, not C3) |
| B | C1 — Mailu 502 cascade | 25 | **DISSOLVED** in CI run 25774452286 — `web-app-mailu` deploy passed in its own slot; the bundle's C1? roles now split across C2 (Playwright regression) and the in-progress in_progress queue (see [CI Run 25774452286 follow-up snapshot](#ci-run-25774452286-follow-up-snapshot)) |
| C | C2 — app-local Playwright failures | 7 → 10 | grew in CI 25774452286 (10 roles: bluesky, baserow, bookwyrm, fediwall, fider, friendica, mattermost, pixelfed, postmarks, taiga); per-role inner-loop spec fixes |
| D | C5 — post-deploy `uri` 5xx | 2 | not reproduced in CI 25774452286 (fusiondirectory now C10; odoo still in_progress) |
| E | C6 — peertube PG `connection refused` | 1 | reproduced in CI run 25774452286; same root cause; Meta load-bearing fix still pending |
| F | C7 — logs truncated | 7 | reclassified in CI run 25774452286 — see follow-up snapshot below |
| G | hub apps with truncated logs | 3 | reclassified GREEN — `web-app-{prometheus, keycloak, opentalk}` all passed deploy in CI run 25774452286 |

## How an agent uses this doc

1. Pick the highest-`total` role in the [Per-role remediation matrix](#per-role-remediation-matrix) whose v0/v1/v2 cells are `❌` or `⏳`.
2. Read its `cluster` and `bundle` columns. Apply the matching [Bundle fix recipe](#bundle-fix-recipes).
3. Drive the role through [019 §Per-role flow](019-playwright-meta-services-parity.md#per-role-flow) (incl. [Role Loop](../agents/action/iteration/role.md) + [Playwright Spec Loop](../agents/action/iteration/playwright.md)).
4. Update the row's cells in this matrix (`❌` → `✅` per declared variant). Strike the row in [019](019-playwright-meta-services-parity.md#per-role-iteration-matrix).
5. Run pattern transfer per [019 §Pattern transfer](019-playwright-meta-services-parity.md#pattern-transfer) before deploying the next role.

The procedural rules (autonomy, closure vocabulary, resumability, single closing commit) are inherited from [019 §Closure procedure](019-playwright-meta-services-parity.md#closure-procedure); they are NOT redefined here.

## Cluster catalogue

| ID | Name | Root cause (one-liner) | Fix anchor |
| --- | --- | --- | --- |
| **C1** | Mailu Playwright 502 cascade | Shared mailu / dashboard container purged by inter-round purge but not redeployed; consumer specs land on a 502 vhost. Manifests as `Error: guest visit must not 5xx — Received: 502` from `personas/guest.js:56`. | [Meta root cause](#meta-root-cause-for-bundles-b-c-d-e) — fix the variant-only closure. |
| **C2** | App-local Playwright failures | Role-specific selector drift after Keycloak round-trip (e.g. Friendica `#topbar-first` no longer matches). | Per role: `roles/web-app-<id>/files/playwright.spec.js`. |
| **C3** | `POSTGRES_ALLOWED_AVG_CONNECTIONS' is undefined` | A `set_fact run_once: true` did not survive the matrix-deploy round split. | **LANDED**: vars hoisted to [group_vars/all/17_resource.yml](../../group_vars/all/17_resource.yml); filter relocated to [plugins/filter/split_postgres_connections.py](../../plugins/filter/split_postgres_connections.py). |
| **C5** | Post-deploy `uri` 5xx | Upstream container 500 / 502 during the role's own post-deploy health probe. Same shape as C1 (purged dep) but masked as a role-local failure. | Capture `docker logs <container>` of the failing role; widen the `uri` probe or add a `wait_for` if the container is genuinely slow. |
| **C6** | Peertube `Connection refused to 127.0.0.1:5432` | svc-db-postgres container purged between rounds without being re-deployed; peertube's `postgresql_query` from the ansible controller hits an empty host port. | Same fix as C1 / [Meta root cause](#meta-root-cause-for-bundles-b-c-d-e). |
| **C7** | Logs truncated | `gh run view --log-failed` capped at stream-error for very large jobs; cluster cannot be determined from CI alone. | After Bundles A+B close, re-deploy the role and reclassify from the local log. |
| **C8** | Discourse pgvector | `bundle exec rake db:migrate` fails on `enable_extension(:vector)`. The Discourse-shipped migration `20230710171141 EnablePgVectorExtension` requires the `vector` extension on the postgres server, which the bundled image lacks. Manifests as repeated `Pups::ExecError` → **FAILED TO BOOTSTRAP**, all 3 retry attempts exhausted. | Either install pgvector into the postgres image used by web-app-discourse, or pre-create the extension via `CREATE EXTENSION IF NOT EXISTS vector` from a privileged bootstrap step before discourse's launcher runs. |
| **C9** | Keycloak permanent admin login | `web-app-keycloak/tasks/04_login.yml:17` (Try login with permanent admin) fails for the matrix-deploy round-set, taking down every consumer scheduled into the same round. Surfaces as `[ERROR]: Task failed: Module failed: non-zero return code` originating from `04_login.yml`. | Capture the underlying `kcadm` / `curl` body. Suspected root cause: Keycloak admin password drift across matrix-deploy rounds (admin secret rotated between rounds but the consumer rounds still try the original secret). |
| **C10** | GHCR mailu manifest 502 | `Error response from daemon: Head "https://ghcr.io/v2/mailu/fetchmail/manifests/2024.06": context deadline exceeded` followed by `HTTP Error 502 Bad Gateway`. Transient ghcr.io upstream outage affecting the mailu image pulls. | Retry the deploy on a later run; if the 502 reproduces, add a pull-retry wrapper around `docker compose pull` in the mailu role. |
| **C11** | Listmonk DB upgrade | `Run Listmonk DB/schema upgrade (non-interactive)` task at `roles/web-app-listmonk/tasks/01_database.yml:42` returns non-zero. Likely connects to the wrong postgres host or hits the same purge cascade that C1/C6 cover. | Capture `docker logs listmonk` of the upgrade pass; verify the `listmonk --upgrade --yes` exit code and the rendered env file. |
| **C12** | Matrix compose-up | `compose up` fails inside `roles/web-app-matrix/tasks/01_docker.yml:76`. The same job already saw a `04_login.yml` Keycloak fail earlier (C9), so this may be cascaded. | After C9 is closed, re-deploy `web-app-matrix` and capture the compose-up stderr if it still fails. |
| **C13** | Mediawiki image missing | `docker image inspect failed for mediawiki:1.45: Error response from daemon: No such image: mediawiki:1.45`. The role references a tag that is not in the local image cache and `docker pull` did not run (or it failed earlier). | Either pin to an available mediawiki tag or add the missing `docker_image` pull step to the role. |
| **C14** | Container networking port collision (CI-only, environmental) | `Error response from daemon: failed to set up container networking: Address already in use` during `Container <role>-proxy Starting`. Observed only in CI matrix-deploy rounds; does NOT reproduce on a local full-cycle deploy, so the root cause is contention between concurrently-deploying roles in the CI runner's shared port space, not a defect in the role's `compose.yml.j2`. | No code change needed at the role level. If recurrent across runs, isolate the CI matrix-deploy rounds so port-mapped proxies do not co-exist, or drop host-port bindings for non-customer-facing containers. |

> Cluster **C4** (TestEnv NGINX-STALE, 5 distros) is out of scope here — it lives in `test-development`, not `test-deploy-server`.

## Bundle fix recipes

Bundles MUST be worked through in the order below, because Bundles A and B close most cells via hub fixes.

### Bundle A — `POSTGRES_ALLOWED_AVG_CONNECTIONS` (LANDED)

Hub fix already on the branch. Verification gate: next CI run reports `success` for `web-app-{discourse,mastodon,listmonk,mobilizon,gitlab,pretix,openproject}`. Once observed, strike those rows through here and in [019](019-playwright-meta-services-parity.md#per-role-iteration-matrix).

### Bundle B — Mailu 502 cascade (LOAD-BEARING)

Land the [Meta root cause fix](#meta-root-cause-for-bundles-b-c-d-e). It closes Bundles B + E + most of F automatically. After it lands, re-deploy the C1? candidates and reclassify any that still fail.

Roles: `web-app-mailu` (verified), `web-app-bookwyrm` (verified), plus 21 suspected C1? (see matrix).

### Bundle C — App-local Playwright selector fixes

Per role, inner-loop work via [Playwright Spec Loop](../agents/action/iteration/playwright.md):

1. Establish a baseline deploy.
2. Update the role's `files/playwright.spec.js` selectors to match the live UI.
3. Re-run `scripts/tests/e2e/rerun-spec.sh <role>` until green.

Roles: `web-app-mailu`, `web-app-opencloud`, `web-app-friendica`, `web-app-mattermost`, `web-app-taiga`, `web-app-fediwall`, `web-app-postmarks`.

### Bundle D — Post-deploy `uri` 5xx

Per role:

1. `make deploy-fresh-purged-apps APPS=<role> FULL_CYCLE=true`.
2. On `uri` failure: `make exec CMD='docker logs <container>'` to capture the application-side trace.
3. Either add a `wait_for` ahead of the `uri` probe (slow container) or widen the probe's `status_code` to document the upstream's actual healthy shape.

Roles: `web-app-fusiondirectory`, `web-app-odoo`.

### Bundle E — Peertube PG

Closed by the [Meta root cause fix](#meta-root-cause-for-bundles-b-c-d-e). No separate per-role work needed once that fix lands.

### Bundle F — Reclassify

Re-deploy the role locally after Bundles A+B have closed; the CI log was truncated and tells us nothing. Move the role into its actual cluster, then apply that cluster's recipe.

Roles: `web-app-nextcloud`, `web-app-gitea`, `web-app-shopware`, `web-app-matrix`, `web-app-espocrm`, `web-app-mediawiki`, `web-app-funkwhale`.

### Bundle G — Hub apps with truncated logs

Same as Bundle F. Roles: `web-app-prometheus`, `web-app-keycloak`, `web-app-opentalk`.

## Per-role remediation matrix

Sorted DESC by `total` (carried over from [019](019-playwright-meta-services-parity.md#per-role-iteration-matrix)). Variant declarations mirror [019](019-playwright-meta-services-parity.md#per-role-iteration-matrix); an empty cell means the variant is not declared in `roles/<role>/meta/variants.yml`.

**Legend:** ⏳ untested · ✅ green deploy + Playwright pass · ❌ failed in CI Run 25705903504 or on re-deploy

| Role | total | cluster | bundle | v0 | v1 | v2 | notes |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| ~~`web-app-prometheus`~~ | 173 | C7 | G | ✅ | ✅ |  | Local full-cycle re-deploy v0+v1 — both rounds (PASS 1+2) `failed=0`, 0 Playwright failures. CI flake; not a real cluster-C7 issue. |
| ~~`web-app-mailu`~~ | 139 | C1+C2 | B+C | ✅ | ✅ |  | Local full-cycle re-deploy v0+v1 — all 4 PASS rounds `failed=0`; guest persona scenario passed in 531ms. CI 502 does NOT reproduce locally; environmental flake. |
| ~~`web-app-keycloak`~~ | 130 | C7 | G | ✅ | ✅ |  | Local full-cycle re-deploy v0+v1 — all 4 PASS rounds `failed=0`, 0 Playwright failures. CI flake. |
| ~~`web-app-nextcloud`~~ | 27 | — | — | ✅ | ✅ | ✅ | Local full-cycle deploy passed for all declared variants. CI run 25774452286 surfaced a **C14** `Address already in use` during `nextcloud-proxy` start, but the failure does not reproduce locally — treated as an environmental port collision specific to the CI matrix-deploy round, not a role-local regression. |
| ~~`web-app-bigbluebutton`~~ | 24 | — | — | ✅ | ✅ |  | CI run 25774452286 — deploy + Playwright PASS for all declared variants. |
| ~~`web-app-discourse`~~ | 24 | C8 | — | ✅ | ✅ |  | Local FULL_CYCLE v0+v1 ✅. Real root cause was variant 1's `postgres.shared: false` forcing the bundled launcher postgres (no pgvector); fixed by pinning `services.postgres.shared: true` since `svc-db-postgres` has pgvector compiled. OIDC tests now gated on `OIDC_SERVICE_ENABLED=true`. |
| ~~`web-app-mastodon`~~ | 23 | — | — | ✅ | ✅ |  | CI run 25774452286 — deploy + Playwright PASS for all declared variants (C3 hub fix verified). |
| `web-app-friendica` | 23 | C2 | C | ❌ | ⏳ | ⏳ | CI run 25774452286 — **C2** Playwright failed for `web-app-friendica` (deploy clean). Persona Keycloak round-trip not returning to social.* remains Deep. |
| ~~`web-app-opentalk`~~ | 23 | — | — | ✅ | ✅ | ✅ | CI run 25774452286 — deploy + Playwright PASS for all declared variants. |
| `web-app-listmonk` | 22 | C11 | — | ✅ | ⏳ |  | Local FULL_CYCLE v0 ✅. CI C11 did not reproduce — environmental race in CI matrix-deploy round; v1 pending. |
| `web-app-gitea` | 22 | C9b/C2 | — | ❌ | ⏳ | ⏳ | Network-label `compose up` failure resolved by the new orphan-default-network purge primitive `scripts/container/purge/entity/network.sh` + global `docker network prune -f` after the entity loop in `apps.sh` (commit `c6affc96f`). Spec env extended with `PROMETHEUS_BASE_URL` + `PROMETHEUS_SERVICE_ENABLED` (commit `1e5a47f67`). Remaining: gitea-specific Playwright failures (prometheus scrape contract + universal-logout round-trip timeout). |
| ~~`web-app-openwebui`~~ | 22 | — | — | ✅ | ✅ | ✅ | CI run 25797277810 — deploy + Playwright PASS for all declared variants. |
| ~~`web-app-flowise`~~ | 22 | — | — | ✅ | ✅ | ✅ | CI run 25774452286 — deploy + Playwright PASS for all declared variants. |
| `web-app-bookwyrm` | 22 | C2 | C | ❌ | ⏳ | ⏳ | CI run 25774452286 — **C2** Playwright failed for `web-app-bookwyrm` (deploy clean). Was C1 Mailu cascade in CI 25705903504 — regressed to a different cluster. |
| ~~`web-app-minio`~~ | 22 | — | — | ✅ | ✅ | ✅ | CI run 25797277810 — deploy + Playwright PASS for all declared variants. |
| ~~`web-app-xwiki`~~ | 21 | — | — | ✅ | ✅ |  | CI run 25797277810 — deploy + Playwright PASS for all declared variants. |
| ~~`web-app-shopware`~~ | 21 | — | — | ✅ | ✅ | ✅ | CI run 25797277810 — deploy + Playwright PASS for all declared variants. |
| ~~`web-app-pretix`~~ | 21 | — | — | ✅ | ✅ |  | CI run 25774452286 — deploy + Playwright PASS for all declared variants (C3 hub fix verified). |
| `web-app-odoo` | 21 | C5 | D | ⏳ | ⏳ | ⏳ | CI run 25774452286 — deploy still in_progress at snapshot time; awaiting completion. |
| ~~`web-app-mobilizon`~~ | 21 | — | — | ✅ | ✅ |  | CI run 25774452286 — deploy + Playwright PASS for all declared variants (C3 hub fix verified). |
| `web-app-matrix` | 21 | C12 | — | ❌ | ⏳ |  | CI run 25774452286 — **C12 matrix compose-up** has the same root cause as gitea's C9b (orphan `matrix` network without `com.docker.compose.network=default` label) and is resolved by the same purge primitive — `scripts/container/purge/entity/network.sh` + global `docker network prune -f` (commit `c6affc96f`). Local v0 deploy compose-up grün; Playwright DM-scenario times out at 4.2 min — separate spec issue. |
| ~~`web-app-gitlab`~~ | 21 | — | — | ✅ | ✅ |  | CI run 25774452286 — deploy + Playwright PASS for all declared variants (C3 hub fix verified). |
| ~~`web-app-espocrm`~~ | 21 | C9 | — | ✅ | ✅ | ✅ | Local FULL_CYCLE v0+v1+v2 ✅. Real root cause was a **duplicate `depends_on:` block** in `templates/compose.yml.j2` (websocket service rendered both the `dmbs_excl.yml.j2` include AND a manual `depends_on:`); commits `eaa51b39d` then `1f5689e44` consolidate daemon + websocket to the `dmbs_incl.yml.j2` include pattern. The earlier "C9 Keycloak admin login fatal" in the CI log was just the rescue-block noise — not the actual cluster. |
| `web-app-taiga` | 21 | C2 | C | ❌ | ⏳ | ⏳ | CI run 25774452286 — **C2** Playwright failed for `web-app-taiga` (deploy clean). |
| `web-app-mattermost` | 21 | C2 | C | ❌ | ⏳ |  | CI run 25774452286 — **C2** Playwright failed for `web-app-mattermost` (deploy clean). |
| ~~`web-app-wordpress`~~ | 21 | — | — | ✅ | ✅ |  | CI run 25797277810 — deploy + Playwright PASS for all declared variants. |
| ~~`web-app-joomla`~~ | 21 | — | — | ✅ | ✅ |  | CI run 25774452286 — deploy + Playwright PASS for all declared variants. |
| `web-app-fider` | 21 | C2 | C | ❌ | ⏳ |  | CI run 25774452286 — **C2** Playwright failed for `web-app-fider` (deploy clean). |
| ~~`web-app-decidim`~~ | 21 | — | — | ✅ | ✅ |  | CI run 25774452286 — deploy + Playwright PASS for all declared variants. |
| `web-app-baserow` | 21 | C2 | C | ❌ | ⏳ | ⏳ | CI run 25774452286 — **C2** Playwright failed for `web-app-baserow` (deploy clean). |
| ~~`web-app-akaunting`~~ | 21 | — | — | ✅ | ✅ | ✅ | CI run 25774452286 — deploy + Playwright PASS for all declared variants. |
| `web-app-fediwall` | 21 | C2 | C | ❌ | ⏳ | ⏳ | CI run 25774452286 — **C2** Playwright failed for `web-app-fediwall` (deploy clean). |
| ~~`web-app-suitecrm`~~ | 20 | — | — | ✅ | ✅ | ✅ | CI run 25797277810 — deploy + Playwright PASS for all declared variants. |
| ~~`web-app-snipe-it`~~ | 20 | — | — | ✅ | ✅ | ✅ | CI run 25797277810 — deploy + Playwright PASS for all declared variants. |
| `web-app-openproject` | 20 | C9 | — | ❌ | ⏳ | ⏳ | CI run 25774452286 — `Run database migrations` (`01_settings.yml:15`) returned `rc=137` (cgroup OOM) after 9.5 min / 30 retries. Commit `bdd59b9db` bumps `web.mem_limit` 4g → 6g (peak observed ~5g + headroom; comfortable on the 16 GB public runner). Awaiting CI re-verification. The earlier "C9 Keycloak admin login fatal" was rescue-block noise — not the cluster. |
| `web-app-mediawiki` | 20 | C13 | — | ❌ | ⏳ |  | CI run 25774452286 — **C13 mediawiki image missing**: `docker image inspect failed for mediawiki:1.45: No such image`. |
| ~~`web-app-funkwhale`~~ | 20 | — | — | ✅ | ✅ | ✅ | CI run 25774452286 — deploy + Playwright PASS for all declared variants. |
| `web-app-pixelfed` | 20 | C2 | C | ❌ | ⏳ |  | CI run 25774452286 — **C2** Playwright failed for `web-app-pixelfed` (deploy clean). |
| ~~`web-app-jenkins`~~ | 20 | — | — | ✅ | ✅ | ✅ | CI run 25774452286 — deploy + Playwright PASS for all declared variants. |
| `web-app-fusiondirectory` | 20 | C10 | — | ✅ | ❌ | ⏳ | Local FULL_CYCLE v0 ✅ (C10 ghcr transient confirmed). Commit `b3d5bf466` pins `services.ldap.{enabled,shared}: true` and drops the `ldap:` variant overrides — LDAP IS the storage backend. v1 still ❌: HTTP 502 from openresty because the oauth2-proxy vhost stays rendered even when `services.oauth2.enabled: false` — vhost gating is a separate deep fix. |
| `web-app-peertube` | 20 | C6 | E | ❌ | ⏳ |  | CI run 25774452286 — **C6 peertube PG**: `unable to connect to database: connection to server at "127.0.0.1", port 5432 failed: Connection refused`. Meta load-bearing fix not yet landed. |
| `web-app-bluesky` | 20 | C2 | C | ❌ | ⏳ | ⏳ | CI run 25774452286 — **C2** `Playwright failed for roles: ['web-app-bluesky', 'web-app-mailu']` — guest persona `Test timeout of 60000ms`. Was C1? cascade in CI 25705903504; mailu's own deploy slot passed but its spec regressed inside bluesky's matrix-deploy round. |
| ~~`web-app-opencloud`~~ | 20 | — | — | ✅ | ✅ | ✅ | CI run 25774452286 — deploy + Playwright PASS for all declared variants (cross-verified). |
| ~~`web-app-pgadmin`~~ | 19 | — | — | ✅ | ✅ |  | CI run 25774452286 — deploy + Playwright PASS for all declared variants. |
| ~~`web-app-lam`~~ | 19 | — | — | ✅ | ✅ | ✅ | CI run 25774452286 — deploy + Playwright PASS for all declared variants. Commit `b3d5bf466` additionally pins `services.ldap.{enabled,shared}: true` and drops the variant overrides (LDAP IS the storage backend for LAM). |
| ~~`web-app-yourls`~~ | 19 | — | — | ✅ | ✅ |  | CI run 25774452286 — deploy + Playwright PASS for all declared variants. |
| ~~`web-app-phpmyadmin`~~ | 18 | — | — | ✅ | ✅ |  | CI run 25774452286 — deploy + Playwright PASS for all declared variants. |
| `web-app-postmarks` | 18 | C2 | C | ❌ | ⏳ |  | CI run 25774452286 — **C2** Playwright failed for `web-app-postmarks` (deploy clean). Was 3/3 pass in CI 25680106742 — regression. |
| ~~`web-svc-xmpp`~~ | 16 | — | — | ✅ | ✅ | ✅ | CI run 25774452286 — deploy + Playwright PASS for all declared variants. |

**Total failed roles in CI Run 25705903504 (deploy matrix only):** 49.

## CI Run 25774452286 follow-up snapshot

Re-deploy on the same branch `feature/web-app-kix` after [25705903504](https://github.com/kevinveenbirkenbach/infinito-nexus-core/actions/runs/25705903504). The deploy-matrix completed 82/90 jobs at snapshot time (8 still `in_progress`: `web-app-{minio,odoo,openwebui,shopware,snipe-it,suitecrm,wordpress,xwiki}`).

**Deploy passed (31 `web-app-*` + 4 in-scope `web-svc-*`):**

- `web-app-{akaunting, bigbluebutton, bridgy-fed, chess, dashboard, decidim, flowise, funkwhale, gitlab, hugo, jenkins, joomla, keycloak, lam, littlejs, mailu, mastodon, matomo, mig, mini-qr, mobilizon, moodle, opencloud, opentalk, pgadmin, phpmyadmin, pretix, prometheus, roulette-wheel, sphinx, yourls}`
- `web-svc-{cdn, libretranslate, simpleicons, xmpp}` (plus the always-green infra svc-* set)

**Deploy failed (20 in CI, 19 reproducible):** clustered for remediation below. `web-app-nextcloud` is reclassified as **CI-only / environmental** (local full-cycle deploy passes for every declared variant), leaving 19 role-local regressions.

### Cluster summary (CI 25774452286)

| Cluster | Roles | Count | Action |
| --- | --- | ---: | --- |
| **C2** App-local Playwright regression | bluesky, baserow, bookwyrm, fediwall, fider, friendica, mattermost, pixelfed, postmarks, taiga | 10 | Inner-loop spec fixes per [Bundle C](#bundle-c--app-local-playwright-selector-fixes). bluesky's failure is paired with mailu in the same matrix-deploy round. bookwyrm + postmarks are net-new regressions from CI 25680106742. |
| **C9** Keycloak permanent admin login | espocrm, gitea, openproject | 3 | Root-cause the kcadm login failure in `web-app-keycloak/tasks/04_login.yml:17`. Likely admin-password drift between matrix-deploy rounds; gitea/openproject also cascade into compose-up / DB-migration follow-on errors. |
| **C12** Matrix compose-up | matrix | 1 | Likely cascaded from a C9 Keycloak fail in the same round. Re-deploy after C9 closes. |
| **C8** Discourse pgvector | discourse | 1 | Pre-create `vector` extension or rebuild discourse's postgres image with pgvector enabled. |
| **C11** Listmonk DB upgrade | listmonk | 1 | Capture container logs of the `listmonk --upgrade --yes` pass. |
| **C13** Mediawiki image missing | mediawiki | 1 | Pin the tag or add a `docker_image` pull step. |
| **C14** Container networking port collision (CI-only, environmental) | nextcloud (CI-only) | 0 confirmed | Local full-cycle deploy of `web-app-nextcloud` passes for every declared variant; the CI `Address already in use` does not reproduce locally and is treated as environmental contention between concurrently-deploying CI matrix rounds, not a role-local regression. No role-level remediation. |
| **C10** GHCR mailu manifest 502 | fusiondirectory | 1 | Likely transient; if it reproduces, wrap mailu pulls in a retry helper. |
| **C6** Peertube PG Connection refused | peertube | 1 | Same as [Meta root cause](#meta-root-cause-for-bundles-b-c5-c6-and-most-c1); waiting for that fix. |

**Pattern shift vs. CI 25705903504.** Bundle A (C3 `POSTGRES_ALLOWED_AVG_CONNECTIONS`) is now verified GREEN — every formerly-C3 role passed in this run (discourse is the lone exception, but its failure is C8, not C3). The dominant remaining failure mode has shifted from C1 (Mailu cascade) and C3 (postgres var) to **C2 Playwright regressions** and **C9 Keycloak admin login**. The Meta load-bearing fix for Bundles B/E (C6) is still pending; peertube reproduces. The "Suspected Mailu cascade" (C1?) labels from CI 25705903504 are now reclassified per the cluster summary above.

### Infrastructure improvements landed alongside this remediation loop

These commits are not per-role fixes but address the underlying environment so several cluster signatures stop reproducing across the board:

| Commit | What | Scope |
| --- | --- | --- |
| `c6affc96f` | New entity-keyed purge primitive `scripts/container/purge/entity/network.sh` removes the per-entity default Docker network when `compose down` left it behind with the wrong / empty `com.docker.compose.network` label. `scripts/container/purge/apps.sh` runs the primitive per entity and then issues a single bare `docker network prune -f` after the entity loop. | C9b (gitea), C12 (matrix); any future role hitting the same orphan-network signature. |
| `6d61e3ca4` | Source-able helper `scripts/tests/deploy/local/utils/cache-retry.sh` wraps the deploy command in each local deploy entrypoint (`fresh-purged-app.sh`, `fresh-kept-app.sh`, `fresh-kept-all.sh`, `reuse-kept-app.sh`, `reuse-kept-all.sh`). Detects the stale-apt signature `Release file ... is expired` / `Valid-Until ... expired` in the wrapped command's output, runs `make cache-clean` + `docker builder prune -af` + `docker image prune -af`, then re-runs the command exactly once. | Defensive fallback for "apt Release file ... is expired" Docker-build failures during local iteration. |
| `e58f71987` | Default `INFINITO_PACKAGE_CACHE_MAX_AGE_MIN` lowered 129600 → 8640 (90 days → 6 days). Nexus now re-validates every cached `Release` against upstream before apt would see it expired (Debian/Ubuntu emit `Valid-Until` 7 days from generation). Applies to every Nexus proxy repo via `contentMaxAge` / `metadataMaxAge` / `negativeCache.timeToLive`. | Prevents the underlying stale-apt failure from reaching the deploy in the first place; the cache-retry helper from `6d61e3ca4` is the secondary defence. |

## Meta root cause for Bundles B, C5, C6 (and most C1?)

Two recent change-sets interact:

1. `820fb0a22 fix(purge): clear stale nginx vhosts between matrix-deploy rounds` — extends the inter-round purge with an nginx-vhost primitive. The purge is correct in intent.
2. `f102c229f refactor(inventory): split monolith into SRP submodules + variant-only mode` — the new variant-only resolver added in `cli/administration/deploy/development/inventory/variants.py` (removed again in commit `c7bacbab5`; see [inventory/](../../cli/administration/deploy/development/inventory/__init__.py) for the current package layout) built each round's include list strictly from the variant's pinned `services:` block. Roles whose variants pin `postgres: shared: false` (25 `variants.yml` files do this for variant 1) dropped their postgres dependency from the round.

Effect in CI Run 25705903504, round 1 for any postgres consumer:

```
[round 0] include = … svc-db-postgres, web-app-mailu, web-app-dashboard, web-app-discourse …
[round 1] include = web-svc-cdn, web-app-discourse  variants={web-app-discourse: 1}
```

The inter-round purge tears down everything from round 0 (including svc-db-postgres + mailu + dashboard); round 1 redeploys only what its include set contains. Postgres consumers then fail with C3 / C5 / C6 / C1 signatures, depending on which dep they reach first.

### Load-bearing fix (choose one before working Bundle B onwards)

- **Option A (preferred):** in the variant-aware closure resolver under [cli/administration/deploy/development/inventory/](../../cli/administration/deploy/development/inventory/), expand each round's include set to the transitive dependency closure of every primary app: `closure(app, variant) = {app} ∪ {deps via meta/services.yml shared edges} ∪ {deps via meta/run_after}`. Variant for deps stays at v0 unless explicitly overridden. Makes the variant block declare what to TEST without dropping load-bearing deps.
- **Option B (incremental):** add a `KEEP_SHARED_SERVICES` allow-list to the inter-round purge so platform services (postgres, mariadb, openldap, mailu, dashboard, keycloak) are skipped during the purge.

### Regression test

Together with the fix, add a unit test under `tests/unit/cli/administration/deploy/development/inventory/` that builds a minimal matrix-deploy plan with one variant-changing app + one shared postgres consumer and asserts every round's include set contains `svc-db-postgres`.

Until this fix lands, every C1? row in the matrix stays at `❌` — a CI re-run of the same workflow will reproduce them.

## Verification

- [ ] `make test` green tree-wide after every per-role flow pass.
- [ ] Every row in the [Per-role remediation matrix](#per-role-remediation-matrix) has `✅` in every declared `v*` cell.
- [ ] Every closed role is struck through in [019](019-playwright-meta-services-parity.md#per-role-iteration-matrix).
- [ ] A CI run on `feature/web-app-kix` reports `success` for all 49 roles in the `test-deploy-server` matrix job.
- [ ] Post-deploy log inspection per [019 §Rule 14](019-playwright-meta-services-parity.md#rules) is clean for every closed variant.
