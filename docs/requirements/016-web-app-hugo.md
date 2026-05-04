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
(`web-app-wordpress`, `web-app-discourse`, …). What it lacks is a
build-then-serve role for static sites. `web-app-hugo` fills that gap:

- **Content** comes from an external Git repository (markdown + theme)
  configured per canonical domain.
- **Build** runs Hugo inside a pinned container; the output is a
  static `public/` directory persisted on a named volume.
- **Serve** runs a minimal nginx (no PHP, no dynamic upstream) bound
  to the canonical domain via the existing reverse-proxy wiring.

This split keeps the runtime image tiny and lets `make deploy` rebuild
content without touching the serving container.

## Naming

- Role directory: `roles/web-app-hugo/`.
- Application ID: `web-app-hugo`.
- Container names: `infinito-hugo-builder` (one-shot build container)
  and `infinito-hugo-web` (long-running nginx serving `public/`).
- Internal hostname inside the compose default network: `hugo-web`.

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

- [ ] `roles/web-app-hugo/` follows the standard layout: `meta/`
      (`main.yml`, `info.yml`, `services.yml`, `server.yml`,
      `schema.yml`, `users.yml`), `tasks/`, `templates/`, `vars/`,
      `files/`, `README.md`, `Administration.md`.
- [ ] `meta/main.yml` declares author, license, and tags consistent
      with sibling `web-app-*` roles.
- [ ] The role registers itself with the dashboard and reverse-proxy
      stack via the same hooks used by `web-app-yourls` and
      `web-app-wordpress` (no bespoke registration path).

### Image & versions

- [ ] Hugo image is pinned to a specific extended-Hugo tag (e.g.
      `hugomods/hugo:exts-<version>`) in `vars/main.yml`. `:latest` is
      forbidden.
- [ ] The serving image is pinned (e.g. `nginx:<version>-alpine`) in
      `vars/main.yml`.
- [ ] Both image references go through `lookup('application', ...)`
      so they appear in the global image-version drift report.

### Configuration surface

- [ ] Each canonical domain in
      `server.domains.canonical['web-app-hugo']` produces an
      independent Hugo site. The list MAY be empty (role becomes a
      no-op) or contain N entries (N independent sites).
- [ ] Per-site configuration in the inventory under
      `applications.web-app-hugo.sites.<canonical-domain>`:
      - `source.repo` (HTTPS Git URL, OPTIONAL; default
        `https://github.com/gohugoio/hugoDocs.git` — see **Default
        site** below)
      - `source.ref` (branch, tag, or commit; OPTIONAL; default
        `master` when `source.repo` is the default, otherwise REQUIRED)
      - `source.subdir` (optional path within the repo; default `.`)
      - `theme.repo` and `theme.ref` (OPTIONAL; if set, cloned into
        `themes/<name>` before build)
      - `hugo.base_url` (OPTIONAL; default derived from the canonical
        domain + scheme)
      - `hugo.environment` (OPTIONAL; default `production`)
      - `hugo.minify` (OPTIONAL boolean; default `true`)
- [ ] `meta/schema.yml` validates the above keys and rejects unknown
      keys with a clear error.

### Default site

- [ ] When the operator enables `web-app-hugo` for a canonical domain
      without specifying `source.repo`, the role MUST clone the
      official Hugo documentation source from
      [github.com/gohugoio/hugoDocs](https://github.com/gohugoio/hugoDocs)
      and build it. Rationale: it is the canonical end-to-end
      validation that the build pipeline works against a real,
      non-trivial Hugo project, and it gives the operator a working
      site on first deploy that can be swapped for their own content
      later by overriding `source.repo` / `source.ref`.
- [ ] The default `source.ref` MUST be a pinned tag (NOT
      `master`/`HEAD`) so deploys are reproducible. The pin is
      declared in `vars/main.yml` and bumped via the standard image-
      version drift report flow. **Initial pin: `v0.148.0`** (commit
      `36e3d7b7b521a165bdbf8f63cd417720f37832c6`, tagged on
      [github.com/gohugoio/hugoDocs](https://github.com/gohugoio/hugoDocs/releases/tag/v0.148.0)).
- [ ] The role README MUST document how to override the default with
      a custom content repo + theme.

### Build pipeline

- [ ] `tasks/` clones (or fetches+resets to) `source.ref` and, if
      configured, `theme.ref` into a per-site working tree under
      a host bind path defined by an env var (`INFINITO_HUGO_HOST_PATH`
      or equivalent, declared in `scripts/meta/env/...`).
- [ ] The builder container runs `hugo --minify -e <environment>
      -b <base_url> -d /public/<canonical-domain>` against the
      per-site working tree. Build output lands on the named volume
      mounted into the serving container at `/usr/share/nginx/html`.
- [ ] The build is **idempotent**: re-running the play with the same
      `source.ref` MUST NOT rebuild if the resolved commit and theme
      commit are unchanged. A change in either ref MUST trigger a
      rebuild.
- [ ] Build failures (Hugo non-zero exit) MUST fail the play and
      MUST NOT replace the previously-served content.

### Serving

- [ ] The nginx serving container exposes one
      `${DOCKER_BIND_HOST}:<port>:80` mapping per canonical domain
      OR a single port plus per-domain `server` blocks; the choice is
      consistent with how other multi-domain `web-app-*` roles do it.
- [ ] The healthcheck reports healthy once `GET /` on the served root
      returns HTTP 200.
- [ ] CSP, `server_tokens off`, and the standard security headers are
      inherited from the existing reverse-proxy wiring without role-
      specific overrides.

### Idempotency & deploy

- [ ] `make deploy` and `make deploy-fresh-purged-apps APPS=web-app-hugo`
      both succeed end-to-end on a host with the role enabled.
- [ ] Running the play twice in a row with no inventory change MUST
      report zero `changed=` for the build step.

### Tests

- [ ] `roles/web-app-hugo/files/playwright.spec.js` exercises:
      - front-page reachability for every canonical domain,
      - canonical-domain redirect (non-canonical → canonical),
      - presence of expected static asset (`/index.html` and one CSS
        file emitted by the theme),
      - CSP baseline (same gate as `web-app-wordpress`).
- [ ] `make test` passes.

### Documentation

- [ ] `roles/web-app-hugo/README.md` documents purpose, content-source
      contract, and how to add a new site (one new canonical domain +
      one new `applications.web-app-hugo.sites.*` block).
- [ ] `roles/web-app-hugo/Administration.md` documents day-2 ops:
      forcing a rebuild, rotating to a new theme ref, debugging a
      failed Hugo build (where to find the build log).
- [ ] [docs/requirements/README.md](README.md) — no change required;
      this file is auto-discovered.

## Out of Scope

- Authoring UI (Hugo has none; content lives in Git).
- Server-side comments, search-as-a-service, or any dynamic backend.
- OIDC / LDAP integration — the served content is public-by-design.
  A future requirement MAY add an oauth2-proxy wrapper for staging
  sites; this requirement does NOT.
- Multi-tenant theme marketplace. Themes are pinned per site via
  `theme.repo` + `theme.ref`.

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
[AGENTS.md](../../AGENTS.md) and follow all instructions in it. The
existing `web-app-yourls` role is the structural reference for compose
wiring; the existing `web-app-wordpress` role is the reference for
multi-domain handling and Playwright gating. Deviating from those
conventions requires explicit justification in the PR description.

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
