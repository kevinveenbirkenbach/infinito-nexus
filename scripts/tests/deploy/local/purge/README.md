# Local Purge Scripts

This is the SPOT for cleanup helpers under `scripts/tests/deploy/local/purge/`.
For other local helpers, use [../README.md](../README.md).

## Entry Points

| Entry point | What it does | Key inputs | Notes |
|---|---|---|---|
| `make container-purge-entity` / `entity.sh` | Purges one or more app entities inside the running container. | `APP`, `INFINITO_CONTAINER` | Used by `make deploy-reuse-purged-app`. |
| `make deploy-reuse-purged-app` | Purges the app entity and then reruns `deploy-reuse-kept-app`. | `APP`, `TEST_DEPLOY_TYPE`, `INFINITO_CONTAINER`, `DEBUG`, `INVENTORY_DIR` | Reuses the existing `devices.yml` inventory. |
| `make container-purge-system` / `inventory.sh` / `web.sh` / `lib.sh` | Removes inventory, web config, and lib state in the running container. | `INFINITO_CONTAINER`, `INVENTORY_DIR` | Destructive cleanup. |

## Script Map

- [entity.sh](entity.sh)
- [inventory.sh](inventory.sh)
- [web.sh](web.sh)
- [lib.sh](lib.sh)
