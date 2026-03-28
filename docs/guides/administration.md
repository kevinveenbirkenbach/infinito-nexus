# Administration Guide

Use this guide to create inventories, run a full deploy, and redeploy an existing environment with `infinito` commands only.

For CLI installation and local setup, see the [Installation Guide](installation.md).

## Full Deploy

Create or refresh the inventory first, then deploy against the generated inventory file.

### Create or Refresh the Inventory

```bash
infinito create inventory /etc/infinito.nexus/inventories/prod \
  --inventory-file /etc/infinito.nexus/inventories/prod/devices.yml \
  --host localhost \
  --ssl-disabled \
  --vars-file inventories/dev.yml \
  --include 'web-app-nextcloud,web-app-keycloak'
```

### Run the Deploy

```bash
infinito deploy dedicated /etc/infinito.nexus/inventories/prod/devices.yml \
  --password-file /etc/infinito.nexus/inventories/prod/.password \
  --log /etc/infinito.nexus/logs \
  --diff \
  -vv
```

## Redeploy

When you need to redeploy after changes, repeat the same two `infinito` commands:

1. Re-run `infinito create inventory ...` to refresh the inventory file and included app list.
2. Re-run `infinito deploy dedicated ...` against the same inventory file.

## Inventory Notes

- Keep one inventory directory per environment.
- Store the password file next to the inventory file.
- Update `--include` whenever the target app set changes.
- Replace `inventories/dev.yml` with the matching vars file for your environment when you add one.
