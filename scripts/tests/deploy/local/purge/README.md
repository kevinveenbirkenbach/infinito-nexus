# Local Purge Scripts

This is the SPOT for cleanup helpers under `scripts/tests/deploy/local/purge/`.
For other local helpers, use [../README.md](../README.md).
For the canonical Make target index that invokes these helpers, see [docs/contributing/tools/makefile.md](../../../../../docs/contributing/tools/makefile.md).

## Entry Points

| Entry point | What it does | Key inputs | Notes |
|---|---|---|---|
| `entity.sh` | Purges one or more app entities inside the running container. | `APP`, `INFINITO_CONTAINER` | Used by the deployment cleanup helpers. |
| `inventory.sh` | Removes the inventory directory in the running container. | `INFINITO_CONTAINER`, `INVENTORY_DIR` | Destructive cleanup. |
| `web.sh` | Removes nginx config and self-signed CA state in the running container. | `INFINITO_CONTAINER` | Destructive cleanup. |
| `lib.sh` | Removes the container lib state. | `INFINITO_CONTAINER` | Destructive cleanup. |

## Script Map

- [entity.sh](entity.sh)
- [inventory.sh](inventory.sh)
- [web.sh](web.sh)
- [lib.sh](lib.sh)
