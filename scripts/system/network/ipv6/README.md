# IPv6 Helpers

This is the SPOT for IPv6 helpers under `scripts/system/network/ipv6/`.
For the canonical Make target index that invokes these helpers, see [docs/contributing/tools/makefile.md](../../../../docs/contributing/tools/makefile.md).

## Entry Points

| Script | What it does |
|---|---|
| `disable.sh` | Disables IPv6 for local development. |
| `disable_with_stack_refresh.sh` | Disables IPv6, restarts `docker.service`, and recreates the running Infinito dev stack when one is active. |
| `restore.sh` | Restores the previous IPv6 settings. |
