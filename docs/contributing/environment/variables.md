# Environment Variables

This page documents the repository-owned environment variables that drive the development stack, local deploy helpers, and container bootstrap flow.

App-specific container variables live next to the role that owns them, usually in `roles/<role>/templates/env.j2`, `roles/<role>/templates/bootstrap.env.j2`, or `roles/<role>/templates/playwright.env.j2`.

## Workflow Inputs

| Variable | Purpose | Default / values | Defined in |
|---|---|---|---|
| `APPS` | Single-app deploy target used by `fresh-kept-app.sh`, `reuse-kept-app.sh`, and `fresh-purged-app.sh`. | Required for single-app flows. | [fresh-kept-app.sh](../../../scripts/tests/deploy/local/deploy/fresh-kept-app.sh), [fresh-purged-app.sh](../../../scripts/tests/deploy/local/deploy/fresh-purged-app.sh), [reuse-kept-app.sh](../../../scripts/tests/deploy/local/deploy/reuse-kept-app.sh), [entity.sh](../../../scripts/tests/deploy/local/purge/entity.sh) |
| `SERVICES_DISABLED` | Space- or comma-separated list of compose service names to disable after inventory creation. Sets `enabled: false` and `shared: false` for every matching service across all applications. Use this to reduce resource usage on low-hardware machines. Example: `SERVICES_DISABLED="oidc ldap matomo"`. | Empty by default (no services disabled). | [services_disabler.py](../../../cli/create/inventory/services_disabler.py) |
| `DEBUG` | Enables debug behavior in local deploy flows. | Boolean; defaults vary by helper. | [fresh-kept-app.sh](../../../scripts/tests/deploy/local/deploy/fresh-kept-app.sh), [reuse-kept-app.sh](../../../scripts/tests/deploy/local/deploy/reuse-kept-app.sh), [reuse-kept-all.sh](../../../scripts/tests/deploy/local/deploy/reuse-kept-all.sh) |
| `DISTROS` | Space-separated distro matrix used by CI input resolution. | `arch debian ubuntu fedora centos` | [defaults.sh](../../../scripts/meta/env/defaults.sh), [input.sh](../../../scripts/meta/resolve/input.sh) |
| `INFINITO_CONTAINER` | Name of the running dev container. | `infinito_nexus_${INFINITO_DISTRO}` | [defaults.sh](../../../scripts/meta/env/defaults.sh), [entity.sh](../../../scripts/tests/deploy/local/purge/entity.sh), [inventory.sh](../../../scripts/tests/deploy/local/purge/inventory.sh), [web.sh](../../../scripts/tests/deploy/local/purge/web.sh), [lib.sh](../../../scripts/tests/deploy/local/purge/lib.sh) |
| `INFINITO_DISTRO` | Selected distro flavor for the dev stack and image tags. | `debian`; accepted values are `arch`, `debian`, `ubuntu`, `fedora`, `centos`. | [defaults.sh](../../../scripts/meta/env/defaults.sh), [fresh-kept-all.sh](../../../scripts/tests/deploy/local/deploy/fresh-kept-all.sh), [fresh-kept-app.sh](../../../scripts/tests/deploy/local/deploy/fresh-kept-app.sh), [fresh-purged-app.sh](../../../scripts/tests/deploy/local/deploy/fresh-purged-app.sh), [reuse-kept-all.sh](../../../scripts/tests/deploy/local/deploy/reuse-kept-all.sh) |
| `INVENTORY_DIR` | Inventory directory used by local deploy helpers. The canonical inventory file inside it is `devices.yml`. | `$HOME/inventories/localhost` when resolved automatically. | [inventory.sh](../../../scripts/meta/env/inventory.sh), [resolve.sh](../../../scripts/inventory/resolve.sh), [fresh-kept-all.sh](../../../scripts/tests/deploy/local/deploy/fresh-kept-all.sh), [fresh-kept-app.sh](../../../scripts/tests/deploy/local/deploy/fresh-kept-app.sh), [fresh-purged-app.sh](../../../scripts/tests/deploy/local/deploy/fresh-purged-app.sh), [reuse-kept-app.sh](../../../scripts/tests/deploy/local/deploy/reuse-kept-app.sh), [reset/inventory.sh](../../../scripts/tests/deploy/local/reset/inventory.sh), [reuse-kept-all.sh](../../../scripts/tests/deploy/local/deploy/reuse-kept-all.sh) |
| `LIMIT_HOST` | Ansible limit pattern for local deploys. | `localhost` | [fresh-kept-all.sh](../../../scripts/tests/deploy/local/deploy/fresh-kept-all.sh), [fresh-kept-app.sh](../../../scripts/tests/deploy/local/deploy/fresh-kept-app.sh), [fresh-purged-app.sh](../../../scripts/tests/deploy/local/deploy/fresh-purged-app.sh), [reuse-kept-app.sh](../../../scripts/tests/deploy/local/deploy/reuse-kept-app.sh), [reuse-kept-all.sh](../../../scripts/tests/deploy/local/deploy/reuse-kept-all.sh) |
| `PYTHON` | Python executable used by helper scripts. | `python3` or the active venv python. | [python.sh](../../../scripts/meta/env/python.sh), [fresh-kept-all.sh](../../../scripts/tests/deploy/local/deploy/fresh-kept-all.sh), [fresh-kept-app.sh](../../../scripts/tests/deploy/local/deploy/fresh-kept-app.sh), [fresh-purged-app.sh](../../../scripts/tests/deploy/local/deploy/fresh-purged-app.sh), [reuse-kept-app.sh](../../../scripts/tests/deploy/local/deploy/reuse-kept-app.sh), [reuse-kept-all.sh](../../../scripts/tests/deploy/local/deploy/reuse-kept-all.sh) |
| `TEST_DEPLOY_TYPE` | Inventory and deploy flavor. | `server`; accepted values are `server`, `workstation`, `universal`. | [defaults.sh](../../../scripts/meta/env/defaults.sh), [input.sh](../../../scripts/meta/resolve/input.sh), [fresh-kept-all.sh](../../../scripts/tests/deploy/local/deploy/fresh-kept-all.sh), [fresh-purged-app.sh](../../../scripts/tests/deploy/local/deploy/fresh-purged-app.sh), [reuse-kept-app.sh](../../../scripts/tests/deploy/local/deploy/reuse-kept-app.sh), [reset/inventory.sh](../../../scripts/tests/deploy/local/reset/inventory.sh), [reuse-kept-all.sh](../../../scripts/tests/deploy/local/deploy/reuse-kept-all.sh) |
| `TEST_PATTERN` | Glob for test discovery. | `test*.py` | [defaults.sh](../../../scripts/meta/env/defaults.sh) |
| `WHITELIST` | Optional app-discovery filter. | Empty by default. | [input.sh](../../../scripts/meta/resolve/input.sh), [fresh-kept-all.sh](../../../scripts/tests/deploy/local/deploy/fresh-kept-all.sh) |

## Runtime And Tooling

| Variable | Purpose | Default / values | Defined in |
|---|---|---|---|
| `IS_WSL2` | Indicates whether the current host looks like WSL2. | `true` or `false`. | [runtime.sh](../../../scripts/meta/env/runtime.sh) |
| `NIX_CONFIG` | Optional pass-through Nix configuration used by build and compose flows. | Optional. | [github.sh](../../../scripts/meta/env/github.sh), [compose.yml](../../../compose.yml) |
| `PIP` | Pip command derived from `PYTHON`. | `${PYTHON} -m pip` | [python.sh](../../../scripts/meta/env/python.sh) |
| `PYTHONPATH` | Python import path for helper scripts. | `.` | [python.sh](../../../scripts/meta/env/python.sh) |
| `RUNNING_ON_ACT` | Runtime flag for `act`-based workflows. | `true` or `false`. | [runtime.sh](../../../scripts/meta/env/runtime.sh) |
| `RUNNING_ON_GITHUB` | Runtime flag for GitHub Actions / CI workflows. | `true` or `false`. | [runtime.sh](../../../scripts/meta/env/runtime.sh) |
| `VENV` | Effective virtualenv path used by the repo. | Active venv or `${VENV_BASE%/}/${VENV_NAME}`. | [python.sh](../../../scripts/meta/env/python.sh) |
| `VENV_BASE` | Base directory used to resolve virtualenv paths. | `/opt/venvs` outside an active venv. | [python.sh](../../../scripts/meta/env/python.sh) |
| `VENV_FALLBACK` | Fallback virtualenv path when no venv is active. | `${VENV_BASE%/}/${VENV_NAME}` | [python.sh](../../../scripts/meta/env/python.sh) |
| `VENV_NAME` | Name of the repo virtualenv. | `infinito` | [python.sh](../../../scripts/meta/env/python.sh) |
| `INFINITO_ENV_DEFAULTS_LOADED` | Loader guard for defaults resolution. | Internal `1` flag. | [defaults.sh](../../../scripts/meta/env/defaults.sh) |
| `INFINITO_ENV_GITHUB_LOADED` | Loader guard for GitHub/Act resolution. | Internal `1` flag. | [github.sh](../../../scripts/meta/env/github.sh) |
| `INFINITO_ENV_INVENTORY_LOADED` | Loader guard for inventory resolution. | Internal `1` flag. | [inventory.sh](../../../scripts/meta/env/inventory.sh) |
| `INFINITO_ENV_LOADED` | Loader guard for `scripts/meta/env/all.sh`. | Internal `1` flag. | [all.sh](../../../scripts/meta/env/all.sh) |
| `INFINITO_ENV_PYTHON_LOADED` | Loader guard for Python resolution. | Internal `1` flag. | [python.sh](../../../scripts/meta/env/python.sh) |
| `INFINITO_ENV_RUNTIME_LOADED` | Loader guard for runtime resolution. | Internal `1` flag. | [runtime.sh](../../../scripts/meta/env/runtime.sh) |

## Compose And Container

| Variable | Purpose | Default / values | Defined in |
|---|---|---|---|
| `DNS_IP` | CoreDNS IP used by the CI compose profile. | Provided by the compose environment. | [compose.yml](../../../compose.yml) |
| `DOMAIN` | Base domain for the local compose stack. | Provided by the compose environment. | [compose.yml](../../../compose.yml) |
| `GIT_SSL_NO_VERIFY` | Keeps Git SSL verification enabled inside the `infinito` container. | `0` | [compose.yml](../../../compose.yml) |
| `INFINITO_COMPILE` | Enables rebuild mode in `scripts/docker/entry.sh`. | `1` builds, `0` skips build. | [github.sh](../../../scripts/meta/env/github.sh), [compose.yml](../../../compose.yml), [entry.sh](../../../scripts/docker/entry.sh) |
| `INFINITO_COMPILE_SILENCE` | Suppresses rebuild output when `INFINITO_COMPILE=1`. | `1` hides build logs. | [entry.sh](../../../scripts/docker/entry.sh) |
| `INFINITO_CONTAINER_NO_CA` | Disables CA injection in the container wrapper. | Truthy values disable CA mounting. | [container.py](../../../roles/sys-svc-container/files/container.py) |
| `INFINITO_DOCKER_MOUNT` | Mount point for the Docker data root inside the stack. | `/var/lib/docker` | [github.sh](../../../scripts/meta/env/github.sh), [compose.yml](../../../compose.yml) |
| `INFINITO_DOCKER_VOLUME` | Host-side Docker volume or mount used by the stack. | `/mnt/docker` on GitHub, `docker` in Compose fallback. | [github.sh](../../../scripts/meta/env/github.sh), [compose.yml](../../../compose.yml) |
| `INFINITO_GHCR_MIRROR_PREFIX` | Prefix used when resolving GHCR mirror image names. | `mirror` | [github.sh](../../../scripts/meta/env/github.sh), [mirrors.py](../../../cli/deploy/development/mirrors.py) |
| `INFINITO_IMAGE` | Full container image reference used by Compose and deploy tooling. | `infinito-${INFINITO_DISTRO}` when unset. | [github.sh](../../../scripts/meta/env/github.sh), [compose.yml](../../../compose.yml), [compose.py](../../../cli/deploy/development/compose.py) |
| `INFINITO_IMAGE_REPOSITORY` | Repository path used to resolve image names and tags. | Derived from repo metadata when not set. | [github.sh](../../../scripts/meta/env/github.sh), [build.sh](../../../scripts/image/build.sh), [cleanup.sh](../../../scripts/image/cleanup.sh) |
| `INFINITO_IMAGE_TAG` | Tag portion of the image reference. | `latest` on GitHub; otherwise unset. | [github.sh](../../../scripts/meta/env/github.sh) |
| `INFINITO_NO_BUILD` | Skips `docker compose up` image building when set to `1`. | `0` or `1`. | [github.sh](../../../scripts/meta/env/github.sh), [compose.py](../../../cli/deploy/development/compose.py) |
| `INFINITO_PATH` | Working directory selected inside the `infinito` container. | Computed at container start. | [entry.sh](../../../scripts/docker/entry.sh) |
| `INFINITO_PULL_POLICY` | Docker Compose pull policy. | `always` on GitHub; Compose default elsewhere. | [github.sh](../../../scripts/meta/env/github.sh), [compose.yml](../../../compose.yml) |
| `INFINITO_SRC_DIR` | Source tree path inside the container. | `/opt/src/infinito` | [Dockerfile](../../../Dockerfile), [compose.yml](../../../compose.yml), [entry.sh](../../../scripts/docker/entry.sh) |
| `INFINITO_WAIT_HEALTH_TIMEOUT_S` | Timeout while waiting for the `infinito` container to become healthy. | `600` seconds. | [compose.py](../../../cli/deploy/development/compose.py) |
| `IP4` | Static IPv4 address assigned to the `infinito` container. | Provided by the compose environment. | [compose.yml](../../../compose.yml) |
| `PYTHONHTTPSVERIFY` | Forces HTTPS certificate verification in the container. | `1` | [compose.yml](../../../compose.yml) |

## Persisted Host Metadata

| Variable | Purpose | Default / values | Defined in |
|---|---|---|---|
| `INFINITO_VERSION` | System version written to `/etc/environment` by the system-version role. | Set to the repository version string. | [main.yml](../../../roles/sys-version/tasks/main.yml) |

## Notes

- The tables above cover the repository-owned workflow and runtime variables.
- Role-specific application env files intentionally stay next to their roles so the app documentation and the generated environment stay in sync.
