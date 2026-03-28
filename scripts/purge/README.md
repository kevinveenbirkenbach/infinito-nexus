# System Purge

This is the SPOT for host and system cleanup helpers under `scripts/purge/`.

## Entry Points

| Entry point | What it does | Key inputs | Notes |
|---|---|---|---|
| `make purge-system` / `system.sh` | Runs the broad low-hardware cleanup pass from the repository root. | `PURGE_WINDOWS_CLEANMGR_SETUP` | Best-effort and safe to rerun. |
| `make purge-all` / `all.sh` | Runs `purge-system` plus the broader repository cleanup bundle. | `APP`, `INFINITO_CONTAINER`, `INVENTORY_DIR`, `PURGE_WINDOWS_CLEANMGR_SETUP` | Best-effort and safe to rerun; container cleanup needs the local stack. |

## Script Map

- [all.sh](all.sh)
- [system.sh](system.sh)
