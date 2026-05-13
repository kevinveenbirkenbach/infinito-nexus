# 020 - CI Run 25705903504 Deploy-Failure Remediation Loop

## Scope

Companion to [019](019-playwright-meta-services-parity.md). Tracks the closure of the 49 `test-deploy-server` matrix-job failures from CI Run [25705903504](https://github.com/kevinveenbirkenbach/infinito-nexus-core/actions/runs/25705903504) on branch `feature/web-app-kix`. When a role role-closes here, strike its row through here AND in [019](019-playwright-meta-services-parity.md#per-role-iteration-matrix).

## Status

| Bundle | Cluster | Roles | State |
| --- | --- | ---: | --- |
| A | C3 — `POSTGRES_ALLOWED_AVG_CONNECTIONS' is undefined` | 7 | hub fix LANDED on this branch (commit 297415e70); awaiting CI re-verification |
| B | C1 — Mailu 502 cascade | 25 | load-bearing fix pending (see [Meta root cause](#meta-root-cause-for-bundles-b-c-d-e)) |
| C | C2 — app-local Playwright failures | 7 | pending; per-role inner loop |
| D | C5 — post-deploy `uri` 5xx | 2 | pending; needs runtime container logs |
| E | C6 — peertube PG `connection refused` | 1 | pending; same root cause as B |
| F | C7 — logs truncated | 7 | reclassify after Bundles A+B; CI logs were truncated by gh-API stream cap |
| G | hub apps with truncated logs | 3 | reclassify after Bundles A+B |

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
| `web-app-prometheus` | 173 | C7 | G | ❌ | ⏳ |  | Log truncated; reclassify after A+B. |
| `web-app-mailu` | 139 | C1+C2 | B+C | ❌ | ⏳ |  | Root of the cascade; admin vhost 502. |
| `web-app-keycloak` | 130 | C7 | G | ❌ | ⏳ |  | Log truncated; reclassify after A+B. |
| `web-app-nextcloud` | 27 | C7 | F | ❌ | ⏳ | ⏳ | Log truncated. |
| `web-app-bigbluebutton` | 24 | C1? | B | ❌ | ⏳ |  | Suspected Mailu cascade. |
| `web-app-discourse` | 24 | C3 | A | ❌ | ⏳ |  | Hub fix landed; awaiting CI. |
| `web-app-mastodon` | 23 | C3 | A | ❌ | ⏳ |  | Hub fix landed; awaiting CI. |
| `web-app-friendica` | 23 | C2 | C | ❌ | ⏳ | ⏳ | `TimeoutError #topbar-first` post-login. |
| `web-app-opentalk` | 23 | C7 | G | ❌ | ⏳ | ⏳ | Log truncated. |
| `web-app-listmonk` | 22 | C3 | A | ❌ | ⏳ |  | Hub fix landed; awaiting CI. |
| `web-app-gitea` | 22 | C7 | F | ❌ | ⏳ | ⏳ | Log truncated. |
| `web-app-openwebui` | 22 | C1? | B | ❌ | ⏳ | ⏳ | Suspected Mailu cascade. |
| `web-app-flowise` | 22 | C1? | B | ❌ | ⏳ | ⏳ | Suspected Mailu cascade. |
| `web-app-bookwyrm` | 22 | C1 | B | ❌ | ⏳ | ⏳ | Verified Mailu cascade. |
| `web-app-minio` | 22 | C1? | B | ❌ | ⏳ | ⏳ | Suspected Mailu cascade. |
| `web-app-xwiki` | 21 | C1? | B | ❌ | ⏳ |  | Suspected Mailu cascade. |
| `web-app-shopware` | 21 | C7 | F | ❌ | ⏳ | ⏳ | Log truncated. |
| `web-app-pretix` | 21 | C3 | A | ❌ | ⏳ |  | Hub fix landed; awaiting CI. |
| `web-app-odoo` | 21 | C5 | D | ❌ | ⏳ | ⏳ | Post-deploy `uri` 500. |
| `web-app-mobilizon` | 21 | C3 | A | ❌ | ⏳ |  | Hub fix landed; awaiting CI. |
| `web-app-matrix` | 21 | C7 | F | ❌ | ⏳ |  | Log truncated. |
| `web-app-gitlab` | 21 | C3 | A | ❌ | ⏳ |  | Hub fix landed; awaiting CI. |
| `web-app-espocrm` | 21 | C7 | F | ❌ | ⏳ | ⏳ | Log truncated. |
| `web-app-taiga` | 21 | C2 | C | ❌ | ⏳ | ⏳ | Universal-logout round-trip not returning to taiga.kanban.* |
| `web-app-mattermost` | 21 | C2 | C | ❌ | ⏳ |  | DM-UI selector / universal-logout round-trip. |
| `web-app-wordpress` | 21 | C1? | B | ❌ | ⏳ |  | Suspected Mailu cascade. |
| `web-app-joomla` | 21 | C1? | B | ❌ | ⏳ |  | Suspected Mailu cascade. |
| `web-app-fider` | 21 | C1? | B | ❌ | ⏳ |  | Suspected Mailu cascade. |
| `web-app-decidim` | 21 | C1? | B | ❌ | ⏳ |  | Suspected Mailu cascade. |
| `web-app-baserow` | 21 | C1? | B | ❌ | ⏳ | ⏳ | Suspected Mailu cascade. |
| `web-app-akaunting` | 21 | C1? | B | ❌ | ⏳ | ⏳ | Suspected Mailu cascade; passed in CI 25680106742. |
| `web-app-fediwall` | 21 | C2 | C | ❌ | ⏳ | ⏳ | App-local spec issue. |
| `web-app-suitecrm` | 20 | C1? | B | ❌ | ⏳ | ⏳ | Suspected Mailu cascade. |
| `web-app-snipe-it` | 20 | C1? | B | ❌ | ⏳ | ⏳ | Suspected Mailu cascade. |
| `web-app-openproject` | 20 | C3 | A | ❌ | ⏳ | ⏳ | Hub fix landed; awaiting CI. |
| `web-app-mediawiki` | 20 | C7 | F | ❌ | ⏳ |  | Log truncated. |
| `web-app-funkwhale` | 20 | C7 | F | ❌ | ⏳ | ⏳ | Log truncated. |
| `web-app-pixelfed` | 20 | C1? | B | ❌ | ⏳ |  | Suspected Mailu cascade. |
| `web-app-jenkins` | 20 | C1? | B | ❌ | ⏳ | ⏳ | Suspected Mailu cascade. |
| `web-app-fusiondirectory` | 20 | C5 | D | ❌ | ⏳ | ⏳ | Post-deploy `uri` 502. |
| `web-app-peertube` | 20 | C6 | E | ❌ | ⏳ |  | PG `connection refused` to 127.0.0.1:5432. |
| `web-app-bluesky` | 20 | C1? | B | ❌ | ⏳ | ⏳ | Suspected Mailu cascade; passed in CI 25680106742. |
| `web-app-opencloud` | 20 | C2 | C | ❌ | ⏳ | ⏳ | App-local spec issue post-auth. |
| `web-app-pgadmin` | 19 | C1? | B | ❌ | ⏳ |  | Suspected Mailu cascade. |
| `web-app-lam` | 19 | C1? | B | ❌ | ⏳ | ⏳ | Suspected Mailu cascade. |
| `web-app-yourls` | 19 | C1? | B | ❌ | ⏳ |  | Suspected Mailu cascade. |
| `web-app-phpmyadmin` | 18 | C1? | B | ❌ | ⏳ |  | Suspected Mailu cascade. |
| `web-app-postmarks` | 18 | C2 | C | ❌ | ⏳ |  | App-local spec issue; passed in CI 25680106742. |
| `web-svc-xmpp` | 16 | C1? | B | ❌ | ⏳ | ⏳ | Suspected Mailu cascade. |

**Total failed roles in CI Run 25705903504 (deploy matrix only):** 49.

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
