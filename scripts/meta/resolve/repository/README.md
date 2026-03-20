# Repository Resolve Scripts

This directory contains repository-specific resolvers used across workflows and shell helpers.

- `name.sh` resolves the concrete repository name once for callers
  It prefers explicit env overrides (`INFINITO_IMAGE_REPOSITORY`, `REPO_PREFIX`) before GitHub or git metadata.
- `owner.sh` resolves the concrete repository owner once for callers

These scripts are the SPOT for repository identity resolution.
