# applications lookup

This page describes how agents handle application defaults after the removal of `group_vars/all/05_applications.yml`.

## Rules

- Application defaults are discovered directly from `roles/*/config/main.yml`.
- Agents MUST edit role-local config sources, not recreate repository-wide generated application dictionaries.
- Runtime consumers MUST access merged application data via `lookup('applications')` or a wrapper built on top of it.
- Inventory overrides still belong in the normal `applications` variable path under inventories, group vars, host vars, or role vars.

## Source Of Truth

- Defaults source: `roles/*/config/main.yml`
- Runtime entry point: [`plugins/lookup/applications.py`](../../../../plugins/lookup/applications.py)
- Shared aggregation helper: [`utils/cache/applications.py`](../../../../utils/cache/applications.py)

## Why

The repository no longer maintains a generated `05_applications.yml` artifact. Keeping defaults close to the owning role reduces duplication and avoids stale generated state.
