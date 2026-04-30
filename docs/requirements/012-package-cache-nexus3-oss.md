# 012 - Package Cache (Nexus 3 OSS)

For the user-facing description of the local cache stack and how it is wired today, see [cache.md](../contributing/environment/cache.md).

## User Story

As a developer running infinito-nexus locally, I want a pull-through
cache for OS, language, and chart packages (apt, pypi, npm, helm, raw,
…) so that re-deploys and fresh-purges do not trigger live upstream
package-manager round-trips, in the same way the existing
[`registry-cache`](../../compose/registry-cache/README.md) already
covers Docker image pulls.

## Dependencies

This requirement is a peer addition to the existing `registry-cache`
service defined in [compose.yml](../../compose.yml) and does NOT modify
or depend on its runtime behaviour. It reuses the same conventions
introduced for `registry-cache`:

- the `cache` compose profile,
- the `Profile` gate in
  [cli/deploy/development/profile.py](../../cli/deploy/development/profile.py),
- the strict `${VAR:?…}` env-var contract documented under the
  cache section of
  [docs/contributing/artefact/files/compose.yml.md](../contributing/artefact/files/compose.yml.md),
- the per-cache env script under `scripts/meta/env/`, sourced via
  [scripts/meta/env/all.sh](../../scripts/meta/env/all.sh).

The `registry-cache` service MUST remain in place after this
requirement lands. See **Coexistence**.

## Background

Package-manager downloads from inside the runner (`apt`, `pip`, `npm`,
`helm`, occasional `curl` against `raw.githubusercontent.com`, etc.)
hit upstream on every deploy. This dominates re-deploy time on slow
links and exposes the dev workflow to upstream outages it could
otherwise ride out.

Format-specific proxies (`devpi`, `verdaccio`, `apt-cacher-ng`,
`pacoloco`, `chartmuseum`) would each cover one slice but multiply the
moving parts. Sonatype **Nexus Repository OSS 3.x** (EPL 1.0) is the
only single-component OSS solution that proxies all relevant formats in
one process.

Nexus 3 OSS is added as a **second** service under the existing `cache`
profile, COMPLEMENTING the registry-cache rather than replacing it.

## Naming

The compose service is named `package-cache` (NOT `nexus`) to avoid
collision with the project name `infinito-nexus`. Container name:
`infinito-package-cache`. Internal hostname inside the compose default
network: `package-cache`.

## Coexistence with `registry-cache`

This requirement explicitly does NOT replace the rpardini-based
registry-cache. Reason: `rpardini/docker-registry-proxy` MITMs every
outbound HTTPS image pull transparently, so `image:` references in
roles work unchanged across all registries. Nexus's `docker-proxy`
repos, in contrast, require client-side rewriting (image refs become
`package-cache:8082/...`) or `registry-mirrors` config that only
covers Docker Hub. Replacing rpardini would either lose multi-registry
transparency or force a sweep over every `image:` field in the tree.

Therefore:

- Docker image pulls continue to flow through `registry-cache`.
- Package downloads (apt/pip/npm/helm/raw) flow through `package-cache`.
- The two services run in parallel, both gated by the `cache` profile.

## Acceptance Criteria

### Service & profile

- [ ] `compose/cache.override.yml` defines the `package-cache` service
      with image pinned to a specific `sonatype/nexus3:<tag>` (NOT
      `:latest`), `container_name` `infinito-package-cache`.
- [ ] The service exposes a healthcheck that reports healthy once
      Nexus's REST API responds 200 on `/service/rest/v1/status`.
- [ ] `package-cache` and `registry-cache` can be active concurrently
      in the same override without port or volume conflict.
- [ ] The `Profile` class in `cli/deploy/development/profile.py`
      activates the `cache` stack for local dev (status quo) and
      inactivates it for CI; the same gate applies to all cache
      services.
- [ ] `infinito.depends_on.package-cache` is `required: false` so the
      runner deploys cleanly when the profile is inactive.

### Env defaults

- [ ] `scripts/meta/env/cache/package.sh` exists and exports
      `INFINITO_PACKAGE_CACHE_HOST_PATH`, `INFINITO_PACKAGE_CACHE_HEAP`,
      `INFINITO_PACKAGE_CACHE_DIRECT_MEM`,
      `INFINITO_PACKAGE_CACHE_BLOBSTORE_MAX`, and
      `INFINITO_PACKAGE_CACHE_ADMIN_PASSWORD`.
- [ ] `scripts/meta/env/cache/package.sh` is sourced by
      `scripts/meta/env/all.sh`.
- [ ] `compose/cache.override.yml` consumes every package-cache env
      var strictly via `${VAR:?…}`. Running `docker compose config`
      without sourcing the env script MUST fail explicitly.

### Bootstrap & repos

- [ ] `scripts/docker/cache/package.sh` exists, is idempotent
      (repeated runs MUST NOT error on already-existing repos), and is
      invoked once on first start under the `cache` profile.
- [ ] On first start, the auto-generated Nexus admin password is
      rotated to the value of `INFINITO_PACKAGE_CACHE_ADMIN_PASSWORD`.
- [ ] On first start, the proxy repositories listed in
      [cache.md](../contributing/environment/cache.md) are created.
- [ ] The blobstore `default` is created with quota
      `INFINITO_PACKAGE_CACHE_BLOBSTORE_MAX`.

### Client wiring

- [ ] Under the `cache` profile, `pip install <pkg>` inside the runner
      pulls through `http://package-cache:8081/repository/pypi-proxy/`.
- [ ] Under the `cache` profile, `npm install <pkg>` inside the runner
      pulls through `http://package-cache:8081/repository/npm-proxy/`.
- [ ] Under the `cache` profile, `apt-get update && apt-get install`
      inside the runner pulls through
      `http://package-cache:8081/repository/apt-…/`.
- [ ] When the `cache` profile is INACTIVE, the override is omitted
      and package managers default to upstream — no failed deploys.

### Coexistence with `registry-cache`

- [ ] This requirement does NOT modify the existing `registry-cache`
      service or its CA / proxy.conf wiring.
- [ ] Docker image pulls continue to flow through `registry-cache`;
      `package-cache` is NOT registered as a Docker registry mirror in
      the runner's dockerd.

### Tests

- [ ] An integration test brings up the `cache` stack, executes a
      representative `pip install` and `apt-get install` inside the
      runner, and verifies the requests were served by `package-cache`.
- [ ] `make test` passes.

### Documentation

- [ ] [cache.md](../contributing/environment/cache.md) describes the
      cache stack as the single user-facing reference; per-service
      READMEs and `compose.yml.md` link to it instead of restating
      its content.

## Frontend (transparent TLS-terminating reverse proxy)

The current shape and scope of the `package-cache-frontend` service
are described in [cache.md](../contributing/environment/cache.md).

## Validation Apps

A mix that exercises apt, pip, npm, and helm during deploy:

| App                  | Why it's in the validation set                                  |
|----------------------|-----------------------------------------------------------------|
| `web-app-mediawiki`  | apt + pip during deploy                                         |
| `web-app-discourse`  | npm + ruby gems (gems hit upstream; everything else cached)     |
| any helm-driven role | exercises the `helm-bitnami` proxy                              |

```bash
APPS="web-app-mediawiki web-app-discourse <helm-driven-role>" \
  make deploy-fresh-purged-apps
```

## Prerequisites

Before starting any implementation work, you MUST read
[AGENTS.md](../../AGENTS.md) and follow all instructions in it. The
existing registry-cache wiring (compose service, env script, profile
gate, ExecStartPre helper, bind-mount-with-`/dev/null`-fallback
pattern) is treated as the structural reference; deviating from those
conventions requires explicit justification in the PR description.

## Commit Policy

- The agent MUST NOT create **any** git commit during implementation.
  No partial commits, no checkpoint commits, no per-step commits.
  The working tree evolves in place until both of the following hold:
  - every Acceptance Criterion in this document is checked off
    (`- [x]`);
  - `make test` is green with no skipped suites.
- At that point, the agent lands the whole change set as a single
  commit (or a tight, related sequence) and then instructs the
  operator to run `git-sign-push` outside the sandbox (per
  [CLAUDE.md](../../CLAUDE.md)). The agent MUST NOT push.
