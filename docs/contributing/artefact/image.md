# Role Image Configuration 🐳

This document is the single source of truth for how Docker images are declared in roles and how they are discovered by the tooling. For role-local access patterns, see [Contributing `image`](../code/role/image.md). For the mirroring pipeline that consumes these declarations, see [mirror.md](mirror.md).

## Two Declaration Formats 📋

A role MAY declare images in two ways depending on how the image is used.

### 1. Compose Service Format — `config/main.yml`

Used for images that are started as part of the role's Docker Compose stack. The image is declared alongside the full service configuration:

```yaml
# roles/<role>/config/main.yml
compose:
  services:
    <service-name>:
      image: <image-name>        # e.g. nextcloud, quay.io/keycloak/keycloak
      version: <tag>             # e.g. latest, 31.0.0
      port: 8080
      # … other compose fields
```

- `image` MUST be the image name as it would appear in a `docker pull` command, without the tag.
- `version` MUST be the tag.
- Images without an explicit registry prefix are treated as Docker Hub images.

### 2. Flat Image Format — `defaults/main.yml`

Used for images that are referenced directly in Ansible tasks or templates rather than through compose (e.g. images pulled and run ad-hoc by a task). These MUST be declared under `defaults/main.yml` as the role-local default mapping. Inventory-side overrides MUST stay separate in `images_overrides.<role>.<service>` and be consumed through `lookup('image', ...)`.

Here, the role name is implicit from the file path `roles/<role>/defaults/main.yml`. The key inside `images:` is therefore the service/image key for that role, not the role name again.

```yaml
# roles/<role>/defaults/main.yml
images:
  <service-name>:              # role name comes from roles/<role>/...
    image: <image-name>         # e.g. mcr.microsoft.com/playwright, postgres
    version: <tag>              # e.g. v1.58.2-noble
```

Roles MUST read these values through `lookup('image', ...)` so inventory-side overrides can stay separate from role-local defaults. See [Contributing `image`](../code/role/image.md) for the runtime contract.

- `image` MUST be the image name as it would appear in a `docker pull` command, without the tag.
- `version` MUST be the tag.
- Images without an explicit registry prefix are treated as Docker Hub images.

#### Why `defaults/` and not `vars/`? 🤔

The `images:` block is meant to hold role-local defaults, not inventory state. Keeping it in `defaults/main.yml` makes that intent explicit and keeps the role-side declaration separate from inventory-side `images_overrides`. Declaring `images:` in `vars/main.yml` would turn those defaults into higher-precedence role variables and make the separation between defaults and overrides much less clear.

## Supported Registries 🌐

The following registries are discovered and mirrored:

| Registry | Example image |
|---|---|
| `docker.io` (Docker Hub) | `postgres`, `nextcloud`, `prom/prometheus` |
| `quay.io` | `quay.io/keycloak/keycloak` |
| `ghcr.io` | `ghcr.io/mastodon/mastodon` |
| `mcr.microsoft.com` | `mcr.microsoft.com/playwright` |

Images from other registries are ignored by the discovery and mirroring tooling.

## Discovery — `iter_role_images()` 🔍

`utils/docker/image_discovery.py` scans all roles and yields `ImageRef` objects:

| Source file | Key path | Used for |
|---|---|---|
| `config/main.yml` | `compose.services.<svc>.image` + `.version` | Compose-managed services |
| `defaults/main.yml` | `images.<svc>.image` + `.version` | Ad-hoc task images |

An `ImageRef` carries: `role`, `service`, `name` (without registry), `version`, `source` (full pull ref), `registry`, and `source_file`.

## Mirror Integration 🪞

After discovery, images are mirrored to GHCR and the mirror URLs are injected back into host variables by the inventory creator.

- `config/main.yml` declarations are resolved back through `mirrors.yml.applications.<role>.compose.services.<service>`
- `defaults/main.yml` declarations are resolved back through `mirrors.yml.images.<role>.<service>` and land in host vars under `images_overrides.<role>.<service>`

See [mirror.md](mirror.md) for the full flow.
