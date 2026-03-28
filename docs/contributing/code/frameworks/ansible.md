# Ansible

Use this section for Ansible-specific guidance that applies across the repository.

## Common

Use these shared rules as the default baseline for role values and path handling.

## Paths

You MUST build filesystem paths with `path_join` instead of concatenating path segments as strings.

## Variables and Constants

These rules keep shared role values explicit, reusable, and easy to read.

- You MUST prefer defining shared fixed role variables once in `vars/main.yml` as the single source of truth instead of recomputing them with `lookup()` or dotted variable composition in `*.j2` or `*.yml`.
- Variables that are defined once and treated as constants MUST be uppercase.

## Role Design

Use this section for role-structure guidance around images, files, and constants.

### Container Images

Use this rule when a role needs a Docker image definition.

- You SHOULD prefer `Dockerfile` over `Dockerfile.j2`; only use `Dockerfile.j2` when build-time templating is genuinely required.

### Image Versions

Use this rule when a role pins container image versions in `roles/web-*/config/main.yml`.

- You MUST keep semver-like image versions current when the upstream image publishes matching newer tags.
- You MUST use `# nocheck: docker-version` directly above a `version:` key only for intentional exceptions that should not be flagged by the lint check.
- You SHOULD prefer explicit version pinning over drifting tags when the role depends on stable, reproducible deploys.

For documentation, comments, semantics, and writing guidance, see [Documentation](../../documentation.md).

For test commands and testing standards, see [Testing and Validation](../../development/testing.md).
