# Package-Cache Frontend (TLS-terminating reverse proxy) 🔐

Transparent TLS-terminating reverse proxy in front of the Sonatype
Nexus 3 OSS [`package-cache`](../package-cache/README.md) service.

## Why a frontend? 🧭

Nexus serves its proxy repos under URLs like
`http://package-cache:8081/repository/<name>/...`. Routing a client
through them ordinarily requires per-client URL rewriting (pip.conf,
.npmrc, apt sources, gem mirror config, …). For pip/npm/apt that
wiring already exists in [`compose/package-cache/`](../package-cache/),
but it does not scale to gem/composer/go/alpine without a per-format
client snippet for each.

The frontend collapses all of those into one mechanism: it owns the
real upstream hostnames (`pypi.org`, `registry.npmjs.org`, …) via
DNS-hijack on the runner, terminates TLS with certs signed by a
dedicated CA, and reverse-proxies onto the matching Nexus repo path.
Clients see the upstream URL they always saw; the cache sits
transparently in between.

Compare with [`registry-cache`](../registry-cache/README.md): same
shape (CA + MITM-by-trust), one layer up. registry-cache covers
Docker image pulls; this covers package-manager pulls.

## Scope: runner-only ⚓

Today the frontend is wired **only** for the `infinito` runner
container. App-service Dockerfile builds executed by the inner
`dockerd` are NOT routed through it — they need their own CA-trust
story (build-time CA injection or a custom build-base image), which
is intentionally deferred to keep this change minimal.

## Activation 🎚️

Active under the `cache` compose profile, gated by
[`profile.py`](../../cli/deploy/development/profile.py):

- Active on developer machines (cross-run cache amortization).
- Inactive in CI runs (`GITHUB_ACTIONS=true`, `RUNNING_ON_GITHUB=true`,
  or `CI=true`).

When inactive, the frontend service is not started and the runner's
`extra_hosts` block is omitted, so package managers default to
upstream traffic with no TLS-trust changes visible.

## Pieces 🧩

- **[upstreams.conf](upstreams.conf)** — nginx config. One server-block
  per upstream hostname → reverse-proxy onto the matching Nexus repo
  path. Bind-mounted into the frontend container at
  `/etc/nginx/conf.d/upstreams.conf`.
- **[scripts/docker/cache/package-frontend-certs.sh](../../scripts/docker/cache/package-frontend-certs.sh)** —
  host-side helper that generates the dedicated CA and per-hostname
  leaf certs idempotently. Invoked from
  [compose.py](../../cli/deploy/development/compose.py) before
  `docker compose up` so the frontend has certs when nginx starts.
- **[scripts/docker/cache/package-frontend-ca.sh](../../scripts/docker/cache/package-frontend-ca.sh)** —
  runner-side helper that installs the CA into the runner's system
  trust store. Invoked from [compose.py](../../cli/deploy/development/compose.py)
  after the stack is healthy, before any deploy step that hits the
  cache via TLS.

## Single source of truth for hostnames 📋

The upstream-hostname list is duplicated in three places that MUST
stay in sync:

1. `HOSTNAMES` array in [package-frontend-certs.sh](../../scripts/docker/cache/package-frontend-certs.sh)
   — generates one leaf cert per entry.
2. `server_name` directives in [upstreams.conf](upstreams.conf) —
   one server-block per hostname.
3. `extra_hosts` block emitted for the `infinito` service by
   [compose.py](../../cli/deploy/development/compose.py) — DNS-hijack
   for the runner.

When adding/removing an upstream, edit all three.

## Env-var contract 🌳

For the env-var contract (host paths for CA + per-hostname certs,
static frontend IP, profile gates), see the Package Cache Frontend
section in [compose.yml.md](../../docs/contributing/artefact/files/compose.yml.md).
