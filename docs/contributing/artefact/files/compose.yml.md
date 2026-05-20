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
- You MUST consume tunable runtime parameters via strict substitution `${VAR:?Run 'make dotenv' to generate the .env single source of truth}`; the default lives in [default.env](../../../../env/default.env). Inline `${VAR:-default}` forms are forbidden and enforced by [test_no_default_substitutions.py](../../../../tests/integration/infrastructure/compose/test_no_default_substitutions.py).
- You MUST NOT hardcode values that differ between operators (paths, image tags, CPU or memory caps).
- You SHOULD annotate non-obvious keys with a short inline comment that explains why they exist, not what they do.
- You MUST document every new env var by adding the row below AND committing a one-line `# ...` comment above its key in [default.env](../../../../env/default.env).

## Environment Variables 📋

All variables consumed by [compose.yml](../../../../compose.yml). The per-variable default + comment lives next to the key in [default.env](../../../../env/default.env) (or [ci.env](../../../../env/ci.env) for CI-stack network defaults); the tables below stay scoped to "what role does this variable play in compose.yml" and stop duplicating the default.

### Image and Runtime

| Variable | Purpose |
|---|---|
| `INFINITO_IMAGE` | Image reference used by the `infinito` service. Composed at runtime by the env generator on GHA, empty locally so the `build:` block builds from source. |
| `INFINITO_PULL_POLICY` | Compose `pull_policy`. Defaults to `never` for local builds, generator overrides to `always` on GHA. |
| `INFINITO_CONTAINER` | Used directly as `container_name`. Derived from `INFINITO_DISTRO` by [infinito_container.py](../../../../utils/env/handlers/infinito_container.py). |
| `INFINITO_COMPILE` | Toggles in-container compilation steps on entry. |
| `INFINITO_COMPILE_SILENCE` | `1` silences the in-container rebuild log when `INFINITO_COMPILE=1`. |
| `NIX_CONFIG` | Build-arg forwarded to the Dockerfile for Nix configuration. Pass-through if set in the calling shell. |

### Resource Caps (OOM Reproduction)

These variables cap the `infinito` container so local runs can reproduce GitHub-hosted runner pressure.
Each default is `0`, which Docker interprets as "unlimited" and is identical to omitting the key.
See [ci.md](../../actions/debugging/ci.md) for runner specs and reproduction profiles.

| Variable | Compose key | Example override |
|---|---|---|
| `INFINITO_MEM_LIMIT` | `mem_limit` | `16g` |
| `INFINITO_MEMSWAP_LIMIT` | `memswap_limit` | `16g` |
| `INFINITO_CPUS` | `cpus` | `4` |

You SHOULD set `INFINITO_MEMSWAP_LIMIT` to the same value as `INFINITO_MEM_LIMIT` to disable swap inflation.
Allowing swap masks OOM conditions that the real runner would hit.

### Storage

| Variable | Purpose |
|---|---|
| `INFINITO_DOCKER_VOLUME` | Named volume (or host path) backing the nested Docker directory. Generator overrides to `/mnt/docker` on GHA. |
| `INFINITO_DOCKER_MOUNT` | Mount point inside the container for the nested Docker data. |

### Caches

For activation, coverage, and operations of the `registry-cache`, `package-cache`, and `package-cache-frontend` services, see [cache.md](../../environment/cache.md).

The env-var contracts each service expects strictly via `${VAR:?…}` (consumed in [compose.yml](../../../../compose.yml) and [compose/cache.override.yml](../../../../compose/cache.override.yml)):

| Variable | Purpose |
|---|---|
| `INFINITO_REGISTRY_CACHE_HOST_PATH` | Host path bind-mounted into `registry-cache` for blob/manifest persistence. |
| `INFINITO_REGISTRY_CACHE_CA_HOST_PATH` | Host path holding the proxy MITM CA bundle. Mounted writable into `registry-cache`, read-only into `infinito`. |
| `INFINITO_REGISTRY_CACHE_MAX_SIZE` | Maximum on-disk size. Computed by [infinito_registry_cache_max_size.py](../../../../utils/env/handlers/infinito_registry_cache_max_size.py) as half the free disk at the cache path, floor `1g`, fallback `2g`. |
| `INFINITO_REGISTRY_CACHE_PROXY_CONF` | Bind source for the systemd drop-in inside `infinito`. Set by the dev tooling to the real `proxy.conf` under the `cache` profile. Driver-injected; not produced by `make dotenv`. |
| `INFINITO_PACKAGE_CACHE_HOST_PATH` | Host path bind-mounted at `/nexus-data`. |
| `INFINITO_PACKAGE_CACHE_HEAP` | JVM heap (`-Xms`/`-Xmx`). Computed as half free RAM, capped `2g`, floor `1g`. |
| `INFINITO_PACKAGE_CACHE_DIRECT_MEM` | `MaxDirectMemorySize`. Mirrors `INFINITO_PACKAGE_CACHE_HEAP`. |
| `INFINITO_PACKAGE_CACHE_BLOBSTORE_MAX` | Soft quota for the default blobstore. Computed as half free disk at the cache path, floor `2g`. |
| `INFINITO_PACKAGE_CACHE_MAX_AGE_MIN` | Cache freshness window in minutes, applied to every Nexus proxy repo (`contentMaxAge`/`metadataMaxAge`/negative-cache TTL). Stays strictly below the 7-day `Valid-Until` window Debian / Ubuntu generate in their apt `Release` files, so `apt-get update` never aborts with "Release file ... is expired". |
| `INFINITO_PACKAGE_CACHE_ADMIN_PASSWORD` | Target value for the rotated Nexus admin password. Default is a stable per-host hash. |
| `INFINITO_PACKAGE_CACHE_PORT` | Host-side port mapped to Nexus REST/UI. Bound to `${INFINITO_BIND_IP}` only. |
| `INFINITO_PACKAGE_CACHE_PIP_CONF` | Bind source for `/etc/pip.conf`. Driver-injected by `make up` under the `cache` profile. |
| `INFINITO_PACKAGE_CACHE_NPMRC` | Bind source for `/root/.npmrc`. Driver-injected. |
| `INFINITO_PACKAGE_CACHE_APT_LIST` | Bind source for `/etc/apt/sources.list.d/package-cache.list`. Driver-injected. |
| `INFINITO_PACKAGE_CACHE_FRONTEND_CA_DIR` | Host directory for the frontend CA. |
| `INFINITO_PACKAGE_CACHE_FRONTEND_CERTS_DIR` | Host directory for per-hostname leaf certs. |
| `INFINITO_PACKAGE_CACHE_FRONTEND_IP` | Static IPv4 address for the frontend on the compose default network. |
| `INFINITO_PACKAGE_CACHE_FRONTEND_CA_FILE` | Bind source for `/opt/package-frontend-ca.crt` inside the runner. Driver-injected. |

### Networking

| Variable | Purpose |
|---|---|
| `INFINITO_DNS_IP` | Static IP assigned to the CoreDNS sidecar and used as the DNS server. Default lives in [ci.env](../../../../env/ci.env). |
| `INFINITO_IP4` | Static IPv4 address assigned to the `infinito` container. Default in [ci.env](../../../../env/ci.env). |
| `INFINITO_DOMAIN` | Base domain exported into the container environment. Default in [ci.env](../../../../env/ci.env). |
| `INFINITO_BIND_IP` | Host address that all published ports bind to. |
| `INFINITO_SUBNET` | IPAM subnet for the default bridge network. |
| `INFINITO_GATEWAY` | IPAM gateway for the default bridge network. |
| `INFINITO_OUTER_NETWORK_MTU` | MTU for the bridge network. Lower when the host network is tunneled. |

## Adding a Variable ➕

When you introduce a new env var in `compose.yml`, you MUST:

1. Add the default + one-line `# ...` comment to [default.env](../../../../env/default.env) (or [ci.env](../../../../env/ci.env) for the CI network block). Defaults never live in `compose.yml`.
2. Consume the variable strictly via `${VAR:?Run 'make dotenv' to generate the .env single source of truth}`; bare `${VAR}` is acceptable only when the value is optional (e.g. `NIX_CONFIG`).
3. Add a row to the matching table above with its compose-side purpose.
4. Cross-link the variable from the relevant workflow page when it exists only to drive a specific workflow (e.g. resource caps link to [ci.md](../../actions/debugging/ci.md)).
