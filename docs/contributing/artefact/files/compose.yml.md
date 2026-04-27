# `compose.yml` 🐳

This page is the SPOT for rules that govern the top-level [compose.yml](../../../../compose.yml) and for the environment variables it consumes.
For general documentation rules (links, writing, RFC 2119 keywords), see [documentation.md](../../documentation.md).
For CI debugging workflows that use these variables, see [ci.md](../../actions/debugging/ci.md).

## Purpose 🎯

The top-level `compose.yml` is scoped to **local development and CI testing only**.
It MUST NOT be used to deploy or run a live Infinito.Nexus stack.
Production deployments MUST go through the Ansible roles and their own rendered compose files under `roles/<role>/templates/`.

Within its scope, `compose.yml` MUST stay a thin orchestration surface for the `infinito` runner container and its CoreDNS sidecar.
It MUST NOT host application roles, fixtures, or test harnesses.

## Structure 📐

- You MUST keep every service in `compose.yml` behind a `profiles:` entry so that `docker compose up` without a profile stays a no-op.
- You MUST expose tunable runtime parameters as env vars with safe defaults inline in the compose key (e.g. `${VAR:-default}`).
- You MUST NOT hardcode values that differ between operators (paths, image tags, CPU or memory caps).
- You SHOULD annotate non-obvious keys with a short inline comment that explains why they exist, not what they do.
- You MUST document every new env var in the table below when you add it to `compose.yml`.

## Environment Variables 📋

All variables consumed by [compose.yml](../../../../compose.yml). Variables without a default are REQUIRED when the `ci` profile is active.

### Image and Runtime

| Variable                 | Default         | Purpose                                                                 |
|--------------------------|-----------------|-------------------------------------------------------------------------|
| `INFINITO_IMAGE`         | none (required) | Image reference used by the `infinito` service.                         |
| `INFINITO_PULL_POLICY`   | `never`         | Compose `pull_policy`. Keep `never` for local builds, `always` for CI.  |
| `INFINITO_CONTAINER`     | none (required) | Used directly as `container_name`. SPOT-derived from `INFINITO_DISTRO` by [defaults.sh](../../../../scripts/meta/env/defaults.sh); compose.yml reads it strictly via `${INFINITO_CONTAINER:?...}`. |
| `INFINITO_COMPILE`       | `1`             | Passed into the container; toggles in-container compilation steps.      |
| `NIX_CONFIG`             | none            | Build-arg forwarded to the Dockerfile for Nix configuration.            |

### Resource Caps (OOM Reproduction)

These variables cap the `infinito` container so local runs can reproduce GitHub-hosted runner pressure.
Each default is `0`, which Docker interprets as "unlimited" and is identical to omitting the key.
See [ci.md](../../actions/debugging/ci.md) for runner specs and reproduction profiles.

| Variable                 | Compose key      | Default | Example |
|--------------------------|------------------|---------|---------|
| `INFINITO_MEM_LIMIT`     | `mem_limit`      | `0`     | `16g`   |
| `INFINITO_MEMSWAP_LIMIT` | `memswap_limit`  | `0`     | `16g`   |
| `INFINITO_CPUS`          | `cpus`           | `0`     | `4`     |

You SHOULD set `INFINITO_MEMSWAP_LIMIT` to the same value as `INFINITO_MEM_LIMIT` to disable swap inflation.
Allowing swap masks OOM conditions that the real runner would hit.

### Storage

| Variable                  | Default            | Purpose                                                          |
|---------------------------|--------------------|------------------------------------------------------------------|
| `INFINITO_DOCKER_VOLUME`  | `docker`           | Named volume (or host path) backing the nested Docker directory. |
| `INFINITO_DOCKER_MOUNT`   | `/var/lib/docker`  | Mount point inside the container for the nested Docker data.     |

### Registry Cache

The `registry-cache` service runs `rpardini/docker-registry-proxy` as a
pull-through MITM proxy in front of every outbound docker registry pull
made by `infinito`'s inner dockerd. Catch-all caching: first request to
any registry (`docker.io`, `ghcr.io`, `quay.io`, `registry.k8s.io`, …)
is fetched and persisted; re-requests are served from cache. The
service sits in the `ci` profile alongside `coredns` and `infinito`, so
it starts and stops with the dev/CI stack.

Wiring inside `infinito` (all bind-mounted directly via `compose.yml`,
no Dockerfile or entry.sh staging, so edits take effect on the next
container start without an image rebuild):

- the registry-cache CA bundle at `/opt/registry-cache-ca` (read-only),
- the systemd drop-in
  [proxy.conf](../../../../compose/registry-cache/proxy.conf) at
  `/etc/systemd/system/docker.service.d/registry-cache-proxy.conf`,
- the install script
  [registry-cache-ca.sh](../../../../scripts/docker/registry-cache-ca.sh)
  at `/usr/local/bin/registry-cache-ca.sh` (must keep its git
  +x bit; bind-mounts preserve host permissions).

The drop-in registers the install script as `ExecStartPre`. dockerd is
gated on `registry-cache` health (`condition: service_healthy`) so the
CA is on disk before `ExecStartPre` runs. Pulls only. Pushes are not
intercepted.

| Variable                                | Default                                | Purpose                                                                                                              |
|-----------------------------------------|----------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| `INFINITO_REGISTRY_CACHE_HOST_PATH`     | `/tmp/infinito/core/registry-cache/mirror`  | Host path bind-mounted into `registry-cache` for blob/manifest persistence.                                          |
| `INFINITO_REGISTRY_CACHE_CA_HOST_PATH`  | `/tmp/infinito/core/registry-cache/ca`      | Host path holding the proxy MITM CA bundle. Mounted writable into `registry-cache`, read-only into `infinito`.       |
| `INFINITO_REGISTRY_CACHE_MAX_SIZE`      | `32g`                                  | Maximum on-disk size of the cache. Older entries are evicted when this is reached.                                   |

### Networking

| Variable                      | Default          | Purpose                                                                |
|-------------------------------|------------------|------------------------------------------------------------------------|
| `DNS_IP`                      | none (required)  | Static IP assigned to the CoreDNS sidecar and used as the DNS server.  |
| `IP4`                         | none (required)  | Static IPv4 address assigned to the `infinito` container.              |
| `DOMAIN`                      | none (required)  | Base domain exported into the container environment.                   |
| `BIND_IP`                     | `127.0.0.1`      | Host address that all published ports bind to.                         |
| `SUBNET`                      | `172.30.0.0/24`  | IPAM subnet for the default bridge network.                            |
| `GATEWAY`                     | `172.30.0.1`     | IPAM gateway for the default bridge network.                           |
| `INFINITO_OUTER_NETWORK_MTU`  | `1500`           | MTU for the bridge network. Lower when the host network is tunneled.   |

## Adding a Variable ➕

When you introduce a new env var in `compose.yml`, you MUST:

1. Use the `${VAR:-default}` form if a sensible default exists. If no default is safe, use `${VAR}` and treat the variable as REQUIRED.
2. Add a row to the matching table above with default and purpose.
3. Cross-link the variable from the relevant workflow page when the variable only exists to drive a specific workflow (e.g. resource caps link to [ci.md](../../actions/debugging/ci.md)).
