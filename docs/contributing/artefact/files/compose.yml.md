# `compose.yml` 🐳

This page documents the rules that govern the top-level [compose.yml](../../../../compose.yml) and the environment variables it consumes.
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
| `INFINITO_CONTAINER`     | none (required) | Used directly as `container_name`. Derived from `INFINITO_DISTRO` by [defaults.sh](../../../../scripts/meta/env/defaults.sh); compose.yml reads it strictly via `${INFINITO_CONTAINER:?...}`. |
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

### Caches

For activation, coverage, and operations of the `registry-cache`, `package-cache`, and `package-cache-frontend` services, see [cache.md](../../environment/cache.md).

The env-var contracts each service expects strictly via `${VAR:?…}` (consumed in [compose.yml](../../../../compose.yml) and [compose/cache.override.yml](../../../../compose/cache.override.yml)):

| Variable                                | Default          | Purpose                                                                                                              |
|-----------------------------------------|------------------|----------------------------------------------------------------------------------------------------------------------|
| `INFINITO_REGISTRY_CACHE_HOST_PATH`     | none (required)  | Host path bind-mounted into `registry-cache` for blob/manifest persistence. Default supplied by [registry.sh](../../../../scripts/meta/env/cache/registry.sh) (`/var/cache/infinito/core/cache/registry/mirror`). |
| `INFINITO_REGISTRY_CACHE_CA_HOST_PATH`  | none (required)  | Host path holding the proxy MITM CA bundle. Mounted writable into `registry-cache`, read-only into `infinito`. Default `/var/cache/infinito/core/cache/registry/ca`. |
| `INFINITO_REGISTRY_CACHE_MAX_SIZE`      | none (required)  | Maximum on-disk size. Default computed by [registry.sh](../../../../scripts/meta/env/cache/registry.sh) as half free disk at the cache path, min `1g`, fallback `2g`. |
| `INFINITO_REGISTRY_CACHE_PROXY_CONF`    | `/dev/null`      | Bind source for the systemd drop-in inside `infinito`. Set to the real `proxy.conf` by the dev tooling under the `cache` profile. |
| `INFINITO_PACKAGE_CACHE_HOST_PATH`      | none (required)  | Host path bind-mounted at `/nexus-data`. Default `/var/cache/infinito/core/cache/package/data`. |
| `INFINITO_PACKAGE_CACHE_HEAP`           | none (required)  | JVM heap (`-Xms`/`-Xmx`). Default half free RAM, capped at `2g`, floor `1g`. |
| `INFINITO_PACKAGE_CACHE_DIRECT_MEM`     | none (required)  | `MaxDirectMemorySize`. Default mirrors `INFINITO_PACKAGE_CACHE_HEAP`. |
| `INFINITO_PACKAGE_CACHE_BLOBSTORE_MAX`  | none (required)  | Soft quota for the default blobstore. Default half free disk at the cache path, floor `2g`. |
| `INFINITO_PACKAGE_CACHE_MAX_AGE_MIN`    | `129600` (= 90 days) | Cache freshness window in minutes, applied to every Nexus proxy repo (`contentMaxAge`/`metadataMaxAge`/negative-cache TTL). |
| `INFINITO_PACKAGE_CACHE_ADMIN_PASSWORD` | none (required)  | Target value for the rotated Nexus admin password. Default is a stable per-host hash. |
| `INFINITO_PACKAGE_CACHE_PORT`           | `8081`           | Host-side port mapped to Nexus REST/UI. Bound to `${BIND_IP}` only. |
| `INFINITO_PACKAGE_CACHE_PIP_CONF`       | `/dev/null`      | Bind source for `/etc/pip.conf`. Set to `compose/package-cache/pip.conf` under `cache`. |
| `INFINITO_PACKAGE_CACHE_NPMRC`          | `/dev/null`      | Bind source for `/root/.npmrc`. Set to `compose/package-cache/npmrc` under `cache`. |
| `INFINITO_PACKAGE_CACHE_APT_LIST`       | `/dev/null`      | Bind source for `/etc/apt/sources.list.d/package-cache.list`. Set to `compose/package-cache/apt.list` under `cache`. |
| `INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR`    | none (required) | Host directory for the frontend CA. Default `/var/cache/infinito/core/cache/package/frontend/ca`. |
| `INFINITO_PACKAGE_CACHE_FRONTEND_CERTS_DIR` | none (required) | Host directory for per-hostname leaf certs. Default `/var/cache/infinito/core/cache/package/frontend/certs`. |
| `INFINITO_PACKAGE_CACHE_FRONTEND_IP`        | none (required) | Static IPv4 address for the frontend on the compose default network. Default `172.30.0.4`. |
| `INFINITO_PACKAGE_CACHE_FRONTEND_CA_FILE`   | `/dev/null`     | Bind source for `/opt/package-frontend-ca.crt` inside the runner. Set to `${INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR}/ca.crt` under `cache`. |

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
