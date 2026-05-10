# Role Image Configuration 🐳

This page describes how Docker images are declared, read, overridden, discovered, and mirrored.
For the mirroring pipeline, see [mirror.md](mirror.md).

## Declaration Format 📋

Every role MUST declare its Docker images in `meta/services.yml`.
The file root IS the services map keyed by `<service-name>` (no `compose:` and no `services:` wrapper):

```yaml
# roles/<role>/meta/services.yml
<service-name>:
  image: <image-name>   # e.g. nextcloud, quay.io/keycloak/keycloak, mcr.microsoft.com/playwright
  version: <tag>        # e.g. latest, 31.0.0, v1.58.2-noble
  ports:
    inter: 8080         # internal container port (per req-009)
  # … other compose fields
```

- `image` MUST be the image name as it appears in a `docker pull` command, without the tag.
- `version` MUST be the tag.
- Images without an explicit registry prefix are treated as Docker Hub images.
- Compose-managed services and ad-hoc task images both live under the same key on the role's primary or auxiliary service entries.
- Role-local image defaults MUST stay in `meta/services.yml`. Inventory-side overrides MUST NOT be written there.

## Read 📖

Roles MUST use `lookup('image', ...)` instead of reading the `meta/services.yml` keys directly.
The lookup MAY infer the current role id from `role_name`.
If `role_name` is not available, the role id MUST be passed explicitly.

Supported forms:

```yaml
{{ lookup('image', 'playwright', 'image') }}
{{ lookup('image', 'test-e2e-playwright', 'playwright', 'image') }}
{{ lookup('image', 'sys-ctl-hlth-csp', 'csp-checker', 'ref') }}
```

Supported `want` values:

| Value | Returns |
|---|---|
| `all` (default) | the merged mapping |
| `image` | the repository/image name |
| `version` | the tag |
| `ref` | `image:version` |

## Override ✏️

Inventory-side mirror and manual overrides MUST be written to `images_overrides.<role>.<service>.{image,version}`.
`lookup('image', ...)` MUST prefer `images_overrides` and fall back field-wise to the role's `meta/services.yml` entry.
Inventory generation MUST keep `images_overrides` separate from `meta/services.yml` so role defaults remain readable and stable.

Example host-vars override:

```yaml
images_overrides:
  test-e2e-playwright:
    playwright:
      image: ghcr.io/example/mirror/mcr.microsoft.com/playwright
      version: v1.58.2-noble
```

## Supported Registries 🌐

The following registries are discovered and mirrored:

| Registry | Example image |
|---|---|
| `docker.io` (Docker Hub) | `postgres`, `nextcloud`, `prom/prometheus` |
| `quay.io` | `quay.io/keycloak/keycloak` |
| `ghcr.io` | `ghcr.io/mastodon/mastodon` |
| `mcr.microsoft.com` | `mcr.microsoft.com/playwright` |

Images from other registries are ignored by the discovery and mirroring tooling.

## Discovery 🔍

`utils/docker/image/discovery.py` scans every `roles/<role>/meta/services.yml` and yields `ImageRef` objects for each top-level service entry that carries both `image` and `version`.

An `ImageRef` carries: `role`, `service`, `name` (without registry), `version`, `source` (full pull ref), `registry`, and `source_file`.

## Mirror Integration 🪞

After discovery, images are mirrored to GHCR and the mirror URLs are injected back into host variables by the inventory creator.
Declarations are resolved back through `mirrors.yml.applications.<role>.services.<service>` and land in host vars at the same path.

See [mirror.md](mirror.md) for the full flow.
