# `image`

This page is the SPOT for role-local non-compose image declarations and runtime access.
Use this page for `defaults/main.yml`, `images_overrides`, and the `lookup('image', ...)` contract.
For discovery and mirroring, see [Role Image Configuration](../../artefact/image.md).

## Declare

- Role-local images that are not sourced from `applications.*.compose.services.*` MUST be declared under `defaults/main.yml` as `images.<service>.{image,version}`.
- Each entry MUST contain both `image` and `version`.
- `image` MAY use an explicit registry such as `mcr.microsoft.com/playwright` or an implicit Docker Hub name such as `postgres`.
- Role-local image defaults MUST stay in `images`. Inventory-side overrides MUST NOT be written there.

Example:

```yaml
# defaults/main.yml
images:
  playwright:
    image: mcr.microsoft.com/playwright
    version: "v1.58.2-noble"
```

## Read

- Roles MUST use `lookup('image', ...)` instead of direct `images[...]` access.
- The lookup MAY infer the current role id from `role_name`.
- If `role_name` is not available, the role id MUST be passed explicitly.

Supported forms:

```yaml
{{ lookup('image', 'playwright', 'image') }}
{{ lookup('image', 'test-e2e-playwright', 'playwright', 'image') }}
{{ lookup('image', 'sys-ctl-hlth-csp', 'csp-checker', 'ref') }}
```

Supported `want` values:

- `all` (default) returns the merged mapping
- `image` returns the repository/image name
- `version` returns the tag
- `ref` returns `image:version`

## Override

- Inventory-side mirror and manual overrides MUST be written to `images_overrides.<role>.<service>.{image,version}`.
- `lookup('image', ...)` MUST prefer `images_overrides` and fall back field-wise to role-local `images`.
- Inventory generation MUST keep `images_overrides` separate from `images` so role defaults remain readable and stable.

Example host-vars override:

```yaml
images_overrides:
  test-e2e-playwright:
    playwright:
      image: ghcr.io/example/mirror/mcr.microsoft.com/playwright
      version: v1.58.2-noble
```
