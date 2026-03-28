# Local Deploy Test Scripts 🧪

This folder contains helpers to test deployments locally against the development Docker Compose stack. Use them for quick iteration on a single app, or for larger "deploy everything" smoke tests. 🚀

For the retry-loop policy and when to switch between fresh and reuse paths, see [Iteration](../../../../docs/agents/action/iteration.md).

⚠️ Safety note: some scripts delete state inside the running container (inventory, app entities, web config, `/var/lib/infinito`). Double-check `INVENTORY_DIR` and `INFINITO_CONTAINER` before running cleanup commands. 🧨

## Host OS Notes 🧩

This local setup is primarily tested on Arch-based Linux distributions. If you are on Windows, macOS, or another Linux distribution, developing inside a Linux VM is recommended for the smoothest experience.

Pull requests are welcome to make the local development environment work consistently across all systems. 🤝

## Prerequisites ✅

- Run commands from the repository root.
- Docker and Docker Compose are available locally.
- `jq` is installed (used by `all.sh` for robust app discovery parsing).

Before running any local test scripts, prepare the dev environment:

```bash
make dev-environment-bootstrap
```

If you have not bootstrapped the repo yet (or after a fresh checkout), run:

```bash
make bootstrap
```

`make` targets automatically load defaults from `scripts/meta/env/all.sh` via `BASH_ENV`. If you run scripts directly, load the defaults yourself:

```bash
source scripts/meta/env/all.sh
```

## Test Comparison Table 🧾

The biggest practical difference between these "tests" is which inventory filename they expect.

| Command | Scope | Uses inventory file | Creates inventory | Deploys | Destructive? |
|---|---:|---|---:|---:|---:|
| `make deploy-fresh-kept-all` | all apps | `${INVENTORY_DIR}/${TEST_DEPLOY_TYPE}.yml` | ✅ | ✅ | ❌ |
| `make container-irefresh-inventory` | all apps | `${INVENTORY_DIR}/${TEST_DEPLOY_TYPE}.yml` | ✅ | ❌ | ✅ (wipes `INVENTORY_DIR`) |
| `make deploy-reuse-kept-all` | all apps | `${INVENTORY_DIR}/servers.yml` | ❌ | ✅ | ❌ |
| `make deploy-fresh-kept-app APP=web-app-nextcloud` | 1 app | `${INVENTORY_DIR}/servers.yml` | ✅ | ✅ | ❌ |
| `make deploy-reuse-kept-app APP=web-app-nextcloud` | 1 app | `${INVENTORY_DIR}/${TEST_DEPLOY_TYPE}.yml` | ❌ | ✅ | ❌ |
| `make deploy-reuse-purged-app APP=web-app-nextcloud` | 1 app | `${INVENTORY_DIR}/${TEST_DEPLOY_TYPE}.yml` | ❌ | ✅ | ⚠️ (purges entity first) |
| `make deploy-fresh-purged-app APP=web-app-nextcloud` | 1 app | `${INVENTORY_DIR}/servers.yml` | ✅ | ✅ | ⚠️ (down/up + purges `matomo` entity) |
| `make container-purge-system` | n/a | n/a | n/a | n/a | ✅ (deletes local deploy artifacts) |

## Quickstart 🚀

### Option A: Easiest single-app run (init + deploy)

This is the most convenient "just deploy one app" entry point:

```bash
make deploy-fresh-kept-app APP=web-app-nextcloud
```

Or, without `make`:

```bash
scripts/tests/deploy/local/app.sh web-app-nextcloud
```

### Option B: Fast single-app iteration (reuse an existing `${TEST_DEPLOY_TYPE}.yml`)

1) Build an inventory for all apps (this wipes and recreates `INVENTORY_DIR`):

```bash
INFINITO_DISTRO=debian TEST_DEPLOY_TYPE=server INVENTORY_DIR="$HOME/inventories/localhost" \
scripts/tests/deploy/local/utils/reset.sh
```

2) Rapid deploy one app against that inventory:

```bash
APP=web-app-nextcloud TEST_DEPLOY_TYPE=server INFINITO_CONTAINER=infinito_nexus_debian DEBUG=true INVENTORY_DIR="$HOME/inventories/localhost" \
scripts/tests/deploy/local/rapid.sh
```

### Option C: Full end-to-end run (discover apps + init inventory + deploy all)

```bash
INFINITO_DISTRO=debian TEST_DEPLOY_TYPE=server INVENTORY_DIR="$HOME/inventories/localhost" \
scripts/tests/deploy/local/all.sh
```

## After A Successful Local Deploy: Trust The CA 🔐

To make your browsers trust the Certificate Authority created by the local Infinito.Nexus container, run:

```bash
make trust-ca
```

After that, restart your browser so it picks up the updated trust store.

## Inventory Filename Conventions (Important) 🗂️

There are two inventory conventions used by the scripts here:

- `servers.yml`: the default created by `infinito create inventory` and used by `cli.deploy.development init/deploy`
- `${TEST_DEPLOY_TYPE}.yml`: used by `all.sh`, `utils/reset.sh`, and `rapid.sh` (so you can keep multiple inventories in one directory)

If a command fails with "inventory not found", it's usually because the previous step created a different inventory filename than the next step expects.

## Common Environment Variables 🧰

- `INFINITO_DISTRO`: `arch|debian|ubuntu|fedora|centos` (default: `debian`)
- `TEST_DEPLOY_TYPE`: `server|workstation|universal` (default: `server`)
- `INVENTORY_DIR`: defaults to `$HOME/inventories/localhost` via `scripts/meta/env/all.sh`
- `INFINITO_CONTAINER`: defaults to `infinito_nexus_${INFINITO_DISTRO}`
- `APP`: application id like `web-app-nextcloud` (required by `rapid.sh` and purge helpers)
- `LIMIT_HOST`: host limit pattern (default: `localhost`, only used by some scripts)
- `DEBUG`: `true|false`
- `WHITELIST`: optional app filter for discovery (`scripts/meta/resolve/apps.sh`)
- `PYTHON`: Python executable used for `cli.deploy.development` calls (often `python3`)

## Scripts In Detail 🔍

### `all.sh`

What it does:
- Starts the dev compose stack (no build).
- Discovers apps on the host (`scripts/meta/resolve/apps.sh`).
- Creates an inventory inside the container at `${INVENTORY_DIR}/${TEST_DEPLOY_TYPE}.yml`.
- Runs `infinito deploy dedicated` for all discovered apps.

Required ENV:
- `INFINITO_DISTRO`, `TEST_DEPLOY_TYPE`, `INVENTORY_DIR`

Optional ENV:
- `LIMIT_HOST` (default: `localhost`)
- `WHITELIST`
- `PYTHON` (recommended)

Example:
```bash
INFINITO_DISTRO=debian TEST_DEPLOY_TYPE=server INVENTORY_DIR="$HOME/inventories/localhost" \
scripts/tests/deploy/local/all.sh
```

---

### `run-all.sh`

What it does:
- Deploys everything contained in an existing inventory file.
- Does not create the inventory (it only deploys).

Required ENV:
- `INFINITO_DISTRO`, `TEST_DEPLOY_TYPE`, `INVENTORY_DIR`

Requires on disk:
- `${INVENTORY_DIR}/servers.yml`
- `${INVENTORY_DIR}/.password`

Optional ENV:
- `LIMIT_HOST` (default: `localhost`)
- `DEBUG` (`true|false`, default: `false`)
- `WHITELIST` (only affects the printed discovery output)

Example:
```bash
INFINITO_DISTRO=debian TEST_DEPLOY_TYPE=server INVENTORY_DIR="$HOME/inventories/localhost" \
scripts/tests/deploy/local/run-all.sh
```

---

### `app.sh`

What it does:
- Ensures the dev stack is up (when-down).
- Runs `entry.sh` inside the container.
- Creates an inventory for a single app (and its deps) using `cli.deploy.development init` (creates `servers.yml`).
- Deploys using `cli.deploy.development deploy` (no teardown/cleanup).

Args:
- `<app-id>` (required), e.g. `web-app-nextcloud`

Optional ENV:
- `INFINITO_DISTRO` (default: `debian`)
- `INVENTORY_DIR` (default from `scripts/meta/env/all.sh`)
- `LIMIT_HOST` (default: `localhost`)
- `DEBUG` (`true|false`, default: `true`)

Examples:
```bash
scripts/tests/deploy/local/app.sh web-app-nextcloud
```

---

### `inspect.sh`

What it does:
- Opens an interactive shell in the running infinito container.
- Optionally runs a one-off command when `INSPECT_CMD` is set.
- Positional arguments are passed through to `docker exec` as the command argv.

Required ENV:
- None, the script loads defaults from `scripts/meta/env/all.sh`.

Optional ENV:
- `INFINITO_DISTRO`
- `INFINITO_CONTAINER`
- `INSPECT_CMD`

Examples:
```bash
scripts/tests/deploy/local/inspect.sh
scripts/tests/deploy/local/inspect.sh whoami
INSPECT_CMD='whoami && id' scripts/tests/deploy/local/inspect.sh
```

---

### `dedicated_distro.sh`

What it does:
- Deploys exactly one app twice against the same stack/inventory:
  - Pass 1: `ASYNC_ENABLED=false`
  - Pass 2: `ASYNC_ENABLED=true`
- Creates and re-initializes the `servers.yml` inventory on both passes.
- Purges shared entities up-front (currently purges the `matomo` entity).

Required ENV:
- `INFINITO_DISTRO`, `INVENTORY_DIR`, `TEST_DEPLOY_TYPE`, `APP`

Optional ENV:
- `PYTHON` (default: `python3`)
- `LIMIT_HOST` (default: `localhost`)

Example:
```bash
INFINITO_DISTRO=debian TEST_DEPLOY_TYPE=server INVENTORY_DIR="$HOME/inventories/localhost" APP=web-app-keycloak \
scripts/tests/deploy/local/dedicated_distro.sh
```

---

### `rapid.sh`

What it does:
- Runs `entry.sh` and a targeted `infinito deploy dedicated` for a single `APP`.
- Reuses `${INVENTORY_DIR}/${TEST_DEPLOY_TYPE}.yml`.

Required ENV:
- `APP`, `TEST_DEPLOY_TYPE`, `INFINITO_CONTAINER`, `DEBUG`, `INVENTORY_DIR`

Example:
```bash
APP=web-app-nextcloud TEST_DEPLOY_TYPE=server INFINITO_CONTAINER=infinito_nexus_debian DEBUG=true INVENTORY_DIR="$HOME/inventories/localhost" \
scripts/tests/deploy/local/rapid.sh
```

---

### `utils/reset.sh`

What it does:
- Discovers apps on the host.
- Starts the dev stack (no build).
- Enters the container, wipes `INVENTORY_DIR`, recreates it, writes `.password`.
- Creates an inventory at `${INVENTORY_DIR}/${TEST_DEPLOY_TYPE}.yml`.

Required ENV:
- `INFINITO_DISTRO`, `TEST_DEPLOY_TYPE`, `INVENTORY_DIR`

Optional ENV:
- `WHITELIST`
- `PYTHON` (recommended)

Example:
```bash
INFINITO_DISTRO=debian TEST_DEPLOY_TYPE=server INVENTORY_DIR="$HOME/inventories/localhost" \
scripts/tests/deploy/local/utils/reset.sh
```

## Cleanup Helpers 🧹

### `utils/purge/entity.sh`

Purges one or more app entities inside the container.

Required ENV:
- `APP` (comma or whitespace separated list)
- `INFINITO_CONTAINER`

Example:
```bash
APP="web-app-nextcloud,web-app-keycloak" INFINITO_CONTAINER=infinito_nexus_debian \
scripts/tests/deploy/local/utils/purge/entity.sh
```

---

### `utils/purge/inventory.sh`

Deletes `INVENTORY_DIR` inside the container.

Required ENV:
- `INFINITO_CONTAINER`, `INVENTORY_DIR`

Example:
```bash
INFINITO_CONTAINER=infinito_nexus_debian INVENTORY_DIR="$HOME/inventories/localhost" \
scripts/tests/deploy/local/utils/purge/inventory.sh
```

---

### `utils/purge/web.sh`

Purges web/nginx configuration inside the container (`scripts/administration/purge_web.sh`).

Required ENV:
- `INFINITO_CONTAINER`

Example:
```bash
INFINITO_CONTAINER=infinito_nexus_debian scripts/tests/deploy/local/utils/purge/web.sh
```

---

### `utils/purge/lib.sh`

Deletes `/var/lib/infinito/` inside the container.

Required ENV:
- `INFINITO_CONTAINER`

Example:
```bash
INFINITO_CONTAINER=infinito_nexus_debian scripts/tests/deploy/local/utils/purge/lib.sh
```
