# Entity Purge

This is the SPOT for entity purge helpers under `scripts/container/purge/entity/`.
Use these scripts for stack-level cleanup inside the running container.
For the canonical Make target index that invokes these helpers, see [make.md](../../../../docs/contributing/tools/make.md).

## Entry Points

| Script | What it does | Key inputs |
|---|---|---|
| `all.sh` | Orchestrates database, compose, and filesystem cleanup. | Stack names, `--wipe-data-only`, `--db-only` |
| `compose.sh` | Stops the compose stack and removes volumes. | Stack names |
| `db.sh` | Drops or truncates the backing database. | Stack names, `--wipe-data-only` |
| `dir.sh` | Removes the stack directory and its volumes. | Stack names |
