# Automated Update Helpers 🔄

This directory contains shell shims that the scheduled `Update: Versions` workflow at [update.yml](../../../.github/workflows/update.yml) invokes once per day to bump pinned upstream versions.

Each script is a thin wrapper around a Python CLI under [cli/contributing/](../../../cli/contributing/).
The CLI does the actual scanning, version comparison, and in-place rewrite of `roles/*/meta/services.yml`; the workflow then checks for a diff and, if any file changed, opens or refreshes a pull request against `main` via [open_update_pr.sh](../open_update_pr.sh).

## Scripts 📄

### `image_versions.sh` 🐳

Bumps semver-based OCI image versions declared as `image:` + `version:` pairs under `roles/*/meta/services.yml`.

Delegates to [docker](../../../cli/contributing/update/docker/), which queries Docker Hub and GHCR for newer tags that share the current tag's depth and flavor.
Tags that carry a `# nocheck: docker-version` marker above their `version:` key are skipped.

### `repository_refs.sh` 🌿

Bumps semver-based git refs declared as `repository:` + `ref:` pairs under `roles/*/meta/services.yml`, at any nesting depth (top-level entity, sub-entity, plugin map).

Delegates to [repository](../../../cli/contributing/update/repository/), which resolves upstream tags via `git ls-remote --tags <repository>`.
Non-semver refs (branches like `master`, `main`, `stable`, commit SHAs) are skipped automatically.
Refs that carry a `# nocheck: repository-version` marker above their `ref:` key are skipped.

## Conventions 📐

Each shim MUST:

- Resolve the repository root relative to its own location so it can run from any working directory.
- Forward every argument it receives to the underlying CLI so `--dry-run` and `--repo-root` keep working from the shell.
- Exit non-zero on CLI failure so the workflow surfaces the error.

Local smoke-test before changing a shim:

```bash
bash scripts/github/update/image_versions.sh --dry-run
bash scripts/github/update/repository_refs.sh --dry-run
```

## Related 🔗

- [README.md](../README.md) for the broader inventory of GitHub workflow helpers.
- [open_update_pr.sh](../open_update_pr.sh) for the shared PR-open/refresh logic both update jobs share.
- [check_git_changes.sh](../check_git_changes.sh) for the diff probe that gates the PR step.
