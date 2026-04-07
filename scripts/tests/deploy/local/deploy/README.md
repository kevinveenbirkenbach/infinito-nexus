# Local Deploy Scripts

This is the SPOT for executable local deploy flows under `scripts/tests/deploy/local/deploy/`.

For other local helpers, use [../README.md](../README.md).
For the canonical Make target index that invokes these helpers, see [docs/contributing/tools/makefile.md](../../../../../docs/contributing/tools/makefile.md).

## Prerequisites

- Run commands from the repository root.
- Docker and Docker Compose are available locally.
- `jq` is installed for the app-discovery step in `fresh-kept-all.sh`.
- If you run scripts directly, load the defaults with `source scripts/meta/env/all.sh`.

## Naming

- `fresh` means the flow creates or refreshes the inventory first.
- `reuse` means the flow uses an already existing inventory.
- `kept` means the stack and app state stay in place.
- `purged` means the flow removes the app or stack state before redeploying.
- `apps` means one or more applications, `all` means every discovered application.

## Entry Points

| Entry point | What it does | Key inputs | Notes |
|---|---|---|---|
| `fresh-kept-all.sh` | Discovers apps, creates `devices.yml`, and deploys all discovered apps. | `INFINITO_DISTRO`, `TEST_DEPLOY_TYPE`, `INVENTORY_DIR` | Fresh all-app inventory path. |
| `reuse-kept-all.sh` | Deploys every app from an existing inventory. | `INFINITO_DISTRO`, `TEST_DEPLOY_TYPE`, `INVENTORY_DIR` | Requires `${INVENTORY_DIR}/devices.yml` and `.password`. |
| `fresh-kept-app.sh <app-id>` | Creates `devices.yml` for one or more apps and deploys them. | `APPS=<app-id>` | Init and deploy path for a specific app set. |
| `reuse-kept-app.sh` | Runs a targeted `infinito deploy dedicated` for one or more apps. | `APPS`, `TEST_DEPLOY_TYPE`, `INFINITO_CONTAINER`, `DEBUG`, `INVENTORY_DIR` | Reuses `devices.yml`. |
| `fresh-purged-app.sh` | Recreates `devices.yml` and deploys one or more apps twice with `ASYNC_ENABLED=false` and `ASYNC_ENABLED=true`. | `INFINITO_DISTRO`, `INVENTORY_DIR`, `TEST_DEPLOY_TYPE`, `APPS` | Baseline and recovery path. |
