# Entity Purge 🗑️

Entity-keyed purge primitives for stack-level cleanup inside the running container.

For the canonical Make target index that invokes these helpers, see [make.md](../../../../docs/contributing/tools/make.md).

## Entry Points 🎯

| Script | What it does | Key inputs |
|---|---|---|
| `compose.sh` | Stops the compose stack and removes volumes. | Stack names |
| `db.sh` | Drops or truncates the backing database. | Stack names, `--wipe-data-only` |
| `dir.sh` | Removes the stack directory and its volumes. | Stack names |
| `nginx.sh` | Removes the per-domain nginx vhost files (http + https) belonging to every app under the entity. Thin wrapper around [nginx_vhosts.py](../../../../utils/cleanup/nginx_vhosts.py). | Stack names |

These primitives are entity-keyed.
The app-keyed orchestrator [apps.sh](../apps.sh) maps app ids to entities and drives them in sequence alongside the token-store wipe in [tokens.py](../../../../utils/cleanup/tokens.py).
