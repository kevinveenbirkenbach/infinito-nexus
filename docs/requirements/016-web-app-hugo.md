# 016 - web-app-hugo (Static Site Generator)

## User Story

As an operator, I want a `web-app-hugo` role that builds and serves
[Hugo](https://gohugo.io/) static sites — one per canonical domain
configured for the role — so that I can host fast, dependency-free
HTML/CSS/JS websites (blogs, marketing pages, documentation portals)
on infinito-nexus with the same lifecycle, deploy, and observability
guarantees as every other `web-app-*` role.

## Background

Hugo is a single-binary static site generator written in Go. It reads
Markdown content plus a theme and emits a fully static `public/`
directory in seconds. There is no runtime application server: once the
site is built, any HTTP server (nginx, caddy, S3, …) can serve it.

The infinito-nexus stack already has long-running CMS roles
(`web-app-wordpress`, `web-app-discourse`, …) and one no-database
static-asset role (`web-app-littlejs`) that clones an upstream Git
repository, builds a custom Docker image around it, and serves the
result via nginx. `web-app-hugo` adopts the same shape and adds Hugo's
build step:

- **Content** comes from an external Git repository (markdown + theme)
  cloned by `sys-stk-full` via `docker_git_repository_*` (same path
  used by `web-app-littlejs`).
- **Build + Serve** are wrapped in a single multi-stage Dockerfile:
  the `builder` stage runs `hugo --minify` against the cloned source;
  the `serve` stage is a pinned `nginx:<version>-alpine` that COPYs
  the builder's `/public/` into `/usr/share/nginx/html`. There is no
  separate long-running build container — `compose build` re-bakes
  the static output whenever the cloned source changes, and `compose
  up` restarts nginx with the new image.

This keeps the runtime container small (just nginx + static files) and
makes "the source ref changed → rebuild" automatic via Docker's layer
cache: `compose build` is a no-op when `services/repository/`'s commit
hash is unchanged.

## Naming

- Role directory: `roles/web-app-hugo/`.
- Application ID: `web-app-hugo`.
- Compose service name: `{{ application_id | get_entity_name }}`
  (resolves to `hugo`); container name: `infinito-hugo`. Same shape
  as `web-app-littlejs`'s single-service container.
- Internal hostname inside the compose default network: `hugo`.

## Scope

V1 (this requirement) implements **single canonical domain** per
deploy — the most common shape for a Hugo site, matching every
existing simple `web-app-*` role in the tree. Multi-canonical-domain
support (one role deploy serving N independent Hugo sites with
distinct `--baseURL`s) is **out of scope** for V1; if needed, a
follow-up requirement adds it as a separate iteration. The role MUST
still validate the `server.domains.canonical` list at deploy time and
fail explicitly if more than one canonical domain is configured.

## Dependencies

- Reuses the existing role-meta layout conventions defined in
  [requirement 008](008-role-meta-layout.md).
- Reuses the standard compose includes
  (`sys-svc-compose/templates/base.yml.j2`,
  `sys-svc-container/templates/...`) — see
  [roles/web-app-yourls/templates/compose.yml.j2](../../roles/web-app-yourls/templates/compose.yml.j2)
  as the structural reference.
- Pulls Hugo from upstream via the `package-cache` profile when active
  (requirement [012](012-package-cache-nexus3-oss.md)). When the
  profile is inactive, the role MUST still deploy by going to upstream
  directly.
- Does NOT require a database, OIDC, or LDAP — the served output is
  fully static.

## Acceptance Criteria

### Role layout

- [x] `roles/web-app-hugo/` follows the standard layout for a
      DB-less, single-service web-app: `meta/` (`main.yml`,
      `info.yml`, `services.yml`, `server.yml`), `tasks/`,
      `templates/`, `vars/`, `files/`, `README.md`,
      `Administration.md`. `schema.yml` / `users.yml` are not
      required (matches `web-app-littlejs` / `web-app-mini-qr`).
- [x] `meta/main.yml` declares author, license, and tags consistent
      with sibling `web-app-*` roles.
- [x] The role registers itself with the dashboard and reverse-proxy
      stack via the same `sys-stk-full` include hook used by
      `web-app-littlejs` (no bespoke registration path).

### Image & versions

- [x] Hugo image is pinned to a specific extended-Hugo tag
      (`hugomods/hugo:exts-0.148.0`) in `meta/services.yml`,
      surfaced through `vars/main.yml` via `lookup('config', …)`.
      `:latest` is forbidden.
- [x] The serving image is pinned (`nginx:1.28.0-alpine`) in
      `meta/services.yml`, surfaced through `vars/main.yml`.
- [x] Both image references go through
      `lookup('config', application_id, 'services.hugo.{image,version,builder_image,builder_version}')`
      — same path used by every other `web-app-*` role — so they
      appear in the global image-version drift report.

### Configuration surface

- [x] `server.domains.canonical` for `web-app-hugo` MUST contain
      exactly one entry. If more than one entry, the play MUST fail
      with a clear "multi-canonical not supported in V1" message.
      (Asserted in `tasks/01_core.yml`.)
- [x] Inventory configuration under
      `applications.web-app-hugo.services.hugo`:
      - `source_repository` (HTTPS Git URL, OPTIONAL; default
        `https://github.com/gohugoio/hugoDocs.git` — see **Default
        site** below)
      - `source_version` (branch, tag, or commit; OPTIONAL; default
        value is the pinned tag from **Default site**)
      - `hugo_environment` (OPTIONAL; default `production`)
      - `hugo_minify` (OPTIONAL boolean; default `true`)
      - Hugo `--baseURL` is derived from
        `lookup('tls', application_id, 'url.base')` — the role's TLS
        URL is single-source-of-truth for the canonical scheme+host
        and an inventory override would silently fight that lookup.
- [x] Theme handling: theme is whatever the upstream content repo
      ships in `themes/` or `go.mod` (Hugo modules). The role does
      NOT clone a separate theme repo in V1 — keeping theme + content
      bundled mirrors how `web-app-littlejs` consumes its upstream
      and avoids per-site theme version drift. A separate theme
      override is deferred to the multi-site follow-up.
- [x] Defaults live in `meta/services.yml` (read via
      `lookup('config', application_id, …)` from `vars/main.yml`),
      not in a role-level schema validator — same convention as
      every other `web-app-*` role.

### Default site

- [x] When the operator enables `web-app-hugo` without overriding
      `services.hugo.source_repository`, the role clones the official
      Hugo documentation source from
      [github.com/gohugoio/hugoDocs](https://github.com/gohugoio/hugoDocs)
      and builds it. Validated end-to-end: Playwright
      `hugo serves rendered HTML with a non-empty <title>` passes
      with the docs theme's homepage title.
- [x] The default `source_version` is a pinned tag (NOT
      `master`/`HEAD`). **Initial pin: `v0.148.0`** (commit
      `36e3d7b7b521a165bdbf8f63cd417720f37832c6`, tagged on
      [github.com/gohugoio/hugoDocs](https://github.com/gohugoio/hugoDocs/releases/tag/v0.148.0)).
      Declared in `meta/services.yml`.
- [x] The role README documents how to override the default with a
      custom content repo + ref.

### Build pipeline

- [x] `tasks/01_core.yml` includes `sys-stk-full` and sets
      `docker_git_repository_address` / `docker_git_repository_version`
      to the inventory-resolved `source_repository` / `source_version`.
      The clone path is the standard `services/repository/` under the
      role's container directory.
- [x] `files/Dockerfile` is a multi-stage build:
      - Stage `builder` (`hugomods/hugo:exts-0.148.0`) installs
        Node.js/npm, runs `npm install` if `package.json` is present
        (hugoDocs uses Hugo's JS pipeline with `import 'alpinejs'`),
        and runs `hugo --minify -e ${HUGO_ENVIRONMENT}
        -b ${HUGO_BASE_URL} -d /public` over the cloned content.
      - Stage `serve` (`nginx:1.28.0-alpine`)
        `COPY --from=builder /public/ /usr/share/nginx/html/`.
- [x] The build is **idempotent**: on a second `deploy-reuse-kept-apps`
      with no inventory change, the git-pull task reports
      `changed: false` (`before == after == 36e3d7b7…`) and no
      `compose build` / `compose up` handler fires.
- [x] Build failures (Hugo non-zero exit) fail `compose build` and
      therefore the play. Because the new image is never produced,
      `compose up` keeps serving the previous image — content never
      flips to a half-built state. Observed during this iteration:
      an npm-modules build error (`Could not resolve "alpinejs"`)
      failed the play with no image swap.

### Serving

- [x] The serving container exposes a single
      `${DOCKER_BIND_HOST}:8008:80` mapping; port allocated via
      `cli meta ports suggest --scope local --category http`.
- [x] The healthcheck uses
      `sys-svc-container/templates/healthcheck/wget.yml.j2`
      (BusyBox wget; the pinned `nginx:1.28.0-alpine` ships no curl).
      Container reports `Up (healthy)` after first deploy.
- [x] CSP (`content-security-policy: default-src 'self'; …`),
      `server: openresty/…` (no version leak from the role's nginx —
      reverse-proxy strips server header), and HSTS
      (`strict-transport-security: max-age=15768000`) are emitted by
      the front proxy. Validated by `curl -sk -I https://hugo.infinito.example/`.

### Idempotency & deploy

- [x] `make deploy-fresh-purged-apps APPS=web-app-hugo FULL_CYCLE=true`
      succeeds end-to-end (`failed=0` in PLAY RECAP).
- [x] Running `make deploy-reuse-kept-apps APPS=web-app-hugo` a
      second time reports zero changes for the Hugo build step: git
      pull `changed: false`, no compose-build / compose-up handler
      fires.

### Tests

- [x] `roles/web-app-hugo/files/playwright.spec.js` exercises:
      - front-page reachability of the canonical domain (HTTP < 400,
        canonical-domain check, HSTS present),
      - non-empty `<title>` + Hugo content sentinel (rejects nginx
        default index / directory listing),
      - CSP header present and non-empty.
      All three pass under the deploy-time
      `test-e2e-playwright` runner (`3 passed`).
- [x] `make test` passes (162 tests, 1 skipped).

### Documentation

- [x] `roles/web-app-hugo/README.md` documents purpose, the default
      content source (hugoDocs), and how to override
      `source_repository` / `source_version` from the inventory.
- [x] `roles/web-app-hugo/Administration.md` documents day-2 ops:
      forcing a rebuild (`docker compose build --no-cache`), bumping
      the source ref, debugging a failed Hugo build (where to find
      the `compose build` log via `make exec`).

## Out of Scope

- Authoring UI (Hugo has none; content lives in Git).
- Server-side comments, search-as-a-service, or any dynamic backend.
- OIDC / LDAP integration — the served content is public-by-design.
  A future requirement MAY add an oauth2-proxy wrapper for staging
  sites; this requirement does NOT.
- Multi-tenant theme marketplace. Themes are bundled with the
  upstream content repository in V1.
- Multi-canonical-domain support. V1 supports one canonical domain
  per role deploy; running multiple Hugo sites concurrently is a
  follow-up requirement.
- Canonical-domain redirect Playwright test. Aliases-to-canonical
  redirect is tested centrally by the proxy stack; the role's spec
  does not duplicate it.

## Validation Apps

A single fresh-purged deploy with one canonical domain and **no**
`source.repo` override is the minimum validation set: the role falls
back to the bundled default (`gohugoio/hugoDocs`, see **Default
site**) and renders the official Hugo documentation site.

```bash
APPS="web-app-hugo" make deploy-fresh-purged-apps
```

Expected outcome: the canonical domain serves the rendered Hugo docs
homepage over HTTPS within the standard deploy timeout. The Playwright
suite asserts the front page is reachable and contains the title
emitted by the docs theme.

## Prerequisites

Before starting any implementation work, you MUST read
[AGENTS.md](../../AGENTS.md) and follow all instructions in it.

**Primary structural reference:** `web-app-littlejs`. It is the
no-database, single-canonical-domain web-app in the tree that already
demonstrates the exact pattern this requirement adopts: clone an
upstream Git repo via `sys-stk-full` + `docker_git_repository_*`,
pass the cloned tree into a custom `files/Dockerfile` as build
context, build a custom image, and serve via nginx. Deviating from
that role's conventions requires explicit justification in the PR
description.

## Commit Policy

- The agent MUST NOT create any git commit during implementation.
  No partial commits, no checkpoint commits, no per-step commits.
  The working tree evolves in place until both of the following hold:
  - every Acceptance Criterion in this document is checked off
    (`- [x]`);
  - `make test` is green with no skipped suites.
- At that point, the agent lands the whole change set as a single
  commit (or a tight, related sequence) and then instructs the
  operator to run `git-sign-push` outside the sandbox (per
  [CLAUDE.md](../../CLAUDE.md)). The agent MUST NOT push.
