# Local Inventory Reset

This is the SPOT for inventory refresh helpers under `scripts/tests/deploy/local/reset/`.
For other local helpers, use [../README.md](../README.md).

## Entry Points

| Entry point | What it does | Key inputs | Notes |
|---|---|---|---|
| `make container-refresh-inventory` / `inventory.sh` | Recreates `devices.yml` for all discovered apps without deploying them. | `INFINITO_DISTRO`, `TEST_DEPLOY_TYPE`, `INVENTORY_DIR` | Rebuilds the local inventory and keeps the runtime `.password` file. |

## Script Map

- [inventory.sh](inventory.sh)
