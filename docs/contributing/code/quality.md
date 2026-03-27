[Back to Code](README.md)

# Code Quality

Use this page for repository-wide guidance on diff shape, readability, cleanup, and linting.

## Diff Quality

- Keep diffs focused, readable, and easy to review.
- Avoid duplicate, conflicting, or purely cosmetic churn unless formatting cleanup is part of the task.
- Prefer semantic improvements that reduce maintenance effort.

## Lint

Use these linting and quality tools where applicable:

- [ruff](https://github.com/astral-sh/ruff)
- [shellcheck](https://github.com/koalaman/shellcheck)
- [hadolint](https://github.com/hadolint/hadolint)

## Repository Lint Rules

Use these repo-wide rules when you add, move, or review files:

- Keep broad folders shallow when that helps readability. Direct children should usually stay at 12 or fewer items per folder.
- Treat structural hubs such as `roles/`, `cli/`, `tests/unit/plugins/filter`, `tests/unit/roles`, `inventories/bundles/servers`, `inventories/bundles/workstations`, `plugins/filter`, `plugins/lookup`, `group_vars/all`, and `.github/workflows` as intentional exceptions when they are used to organize the tree.
- Prefer smaller, more focused folders over dumping many unrelated files into one directory.

For refactoring guidance, see [Development](../development/README.md).
