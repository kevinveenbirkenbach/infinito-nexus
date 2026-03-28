# Local Deploy Test Scripts 🧪

This folder is the SPOT for local deploy script entry points.

For retry-loop policy and refresh-vs-reuse decisions, use [Iteration](../../../../docs/agents/action/iteration.md).
For validation strategy, Playwright expectations, and the preferred local deploy checks, use [Testing and Validation](../../../../docs/contributing/development/testing.md).
For bootstrap, CA trust, and host setup, use [Development Environment Setup](../../../../docs/contributing/environment/setup.md).
For low-resource guidance, use [Manage Low-Hardware Resources](../../../../docs/contributing/environment/hardware.md).

⚠️ Safety note: some scripts delete state inside the running container (inventory, app entities, web config, `/var/lib/infinito`). Double-check `INVENTORY_DIR` and `INFINITO_CONTAINER` before running cleanup commands. 🧨

## Host OS Notes 🧩

This local setup is primarily tested on Arch-based Linux distributions. If you are on Windows, macOS, or another Linux distribution, developing inside a Linux VM is recommended for the smoothest experience.

Pull requests are welcome to make the local development environment work consistently across all systems. 🤝

## Prerequisites ✅

- Run commands from the repository root.
- Docker and Docker Compose are available locally.
- `jq` is installed (used by `all.sh` for robust app discovery parsing).
- If you run scripts directly, load the defaults with `source scripts/meta/env/all.sh`.

## Command Index 🧭

| Entry point | What it does | Key inputs | Notes |
|---|---|---|---|
| `make deploy-fresh-kept-all` / `scripts/tests/deploy/local/all.sh` | Starts the dev stack, discovers apps, creates `${TEST_DEPLOY_TYPE}.yml`, and deploys all discovered apps. | `INFINITO_DISTRO`, `TEST_DEPLOY_TYPE`, `INVENTORY_DIR` | Fresh all-app inventory path. |
| `make container-irefresh-inventory` / `scripts/tests/deploy/local/utils/reset.sh` | Recreates the local inventory without deploying apps. | `INFINITO_DISTRO`, `TEST_DEPLOY_TYPE`, `INVENTORY_DIR` | Wipes `INVENTORY_DIR`. |
| `make deploy-reuse-kept-all` / `scripts/tests/deploy/local/run-all.sh` | Deploys every app from an existing inventory. | `INFINITO_DISTRO`, `TEST_DEPLOY_TYPE`, `INVENTORY_DIR` | Requires `${INVENTORY_DIR}/servers.yml` and `.password`. |
| `make deploy-fresh-kept-app` / `scripts/tests/deploy/local/app.sh <app-id>` | Creates `servers.yml` for one app and deploys it. | `APP=<app-id>` | Single-app init and deploy path. |
| `make deploy-reuse-kept-app` / `scripts/tests/deploy/local/rapid.sh` | Runs a targeted `infinito deploy dedicated` for one app. | `APP`, `TEST_DEPLOY_TYPE`, `INFINITO_CONTAINER`, `DEBUG`, `INVENTORY_DIR` | Reuses `${TEST_DEPLOY_TYPE}.yml`. |
| `make deploy-reuse-purged-app` | Purges one app entity and then reruns `deploy-reuse-kept-app`. | `APP`, `TEST_DEPLOY_TYPE`, `INFINITO_CONTAINER`, `DEBUG`, `INVENTORY_DIR` | Purge helper plus reuse path. |
| `make deploy-fresh-purged-app` / `scripts/tests/deploy/local/dedicated_distro.sh` | Recreates `servers.yml` and deploys one app twice with `ASYNC_ENABLED=false` and `ASYNC_ENABLED=true`. | `INFINITO_DISTRO`, `INVENTORY_DIR`, `TEST_DEPLOY_TYPE`, `APP` | Also purges shared entities up front. |
| `make container-purge-system` | Deletes local deploy artifacts and cleanup data. | n/a | Destructive cleanup. |
| `scripts/tests/deploy/local/inspect.sh` | Opens an interactive shell or runs a one-off command in the running container. | Optional `INSPECT_CMD` or positional args | Uses `scripts/meta/env/all.sh` defaults. |

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
