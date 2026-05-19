# Infinito.Nexus Inventories

This directory contains all deployable bundles for Infinito.Nexus.

An inventory in Infinito.Nexus is not just a host definition.
It represents a complete, declarative infrastructure bundle.

Each inventory defines:

- Which roles are activated
- Which host(s) are targeted
- Metadata required by the Infinito Deployer (title, description, logo, etc.)

Deploy target is derived from the folder structure.

---

## Directory Structure

Inventories are grouped by deploy target:

inventories/
  server/
  workstation/

Each bundle must live inside one of those directories:

inventories/server/<bundle-name>/
inventories/workstation/<bundle-name>/

The folder name represents the bundle identifier.

---

## Required Files

Each bundle directory must contain:

- inventory.yml

Optional but recommended:

- README.md (bundle-specific documentation)

No additional bundle manifest files are required.

---

## Inventory Structure (Bundle-Conform)

Each inventory must follow this structure:

- all.vars.infinito.bundle metadata
- one default host
- role groups under children

Example:

```yaml
all:
  vars:
    infinito:
      bundle:
        title: "School Basic"
        description: >
          Basic bundle for a small school setup.
        logo:
          class: "fa-solid fa-graduation-cap"
        tags:
          - education
          - collaboration
        categories:
          - Community
          - Collaboration

  hosts:
    server:

  children:
    web-app-nextcloud:
      hosts:
        server:

    svc-prx-openresty:
      hosts:
        server:
```

---

## Rules

### 1. Deploy Target

Deploy target is derived from the parent folder:

- inventories/server → server bundle
- inventories/workstation → workstation bundle

Do not define deploy_target inside the inventory file.

---

### 2. Host Definition

Each bundle must define exactly one default host:

server

No additional configuration is required.

Connection settings may be added later if needed.

---

### 3. Role Activation

Role names must be defined as group names under children.

Group name must match the role directory name exactly.

Each role group must contain the default host.

---

### 4. Bundle Metadata

Metadata must be defined under:

all.vars.infinito.bundle

Required fields:

- title
- description
- logo.class
- tags
- categories

The logo must use a valid Font Awesome class string, e.g.:

fa-solid fa-graduation-cap

---

### 5. No Role-Specific Configuration

Bundles act as skeleton definitions.

They must not contain application-specific configuration values.

Role configuration belongs inside roles or runtime overlays.

---

## Philosophy

An inventory in Infinito.Nexus is:

- a bundle definition
- a role activation map
- a deployable unit

No additional bundle file format is required.

The inventory itself is the bundle.

---

## Deploying a Bundle

Two `make` targets resolve one or more bundles into the role groups declared under `all.children` and feed them into the standard local deploy flow. The resolver is [`utils.inventory.bundle_apps`](../../utils/inventory/bundle_apps.py); it deduplicates across bundles and preserves declaration order.

| Command | Path | Behavior |
|---|---|---|
| `BUNDLES="<a>[,<b>]" make deploy-bundles` | fresh-purged | Brings the stack down/up, purges entities, then deploys every role group from the listed bundles. Set `FULL_CYCLE=true` to also run the async update pass. |
| `BUNDLES="<a>[,<b>]" make redeploy-bundles` | reuse-kept | No down/up, no entity purge. Requires a prior `deploy-bundles` run that initialized the inventory. |

Example:

```bash
BUNDLES="education-suite,startup-essentials" make deploy-bundles FULL_CYCLE=true
```

See [docs/contributing/tools/make.md](../../docs/contributing/tools/make.md) and [docs/contributing/actions/testing.md](../../docs/contributing/actions/testing.md) for the full deploy-target reference.
