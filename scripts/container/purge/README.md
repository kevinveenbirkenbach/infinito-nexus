# Container Purge

This is the SPOT for container-local cleanup helpers under `scripts/container/purge/`.
These scripts run inside the local infinito container and remove container-local state only.
For the canonical Make target index that invokes these helpers, see [docs/contributing/tools/makefile.md](../../../docs/contributing/tools/makefile.md).

## Entry Points

| Entry point | What it does | Notes |
|---|---|---|
| `web.sh` | Removes nginx and self-signed CA state inside the container. | Called by the local purge wrapper. |
| `entity/` | Purges app or stack data inside the container. | See the child directory README for the exact scripts. |
