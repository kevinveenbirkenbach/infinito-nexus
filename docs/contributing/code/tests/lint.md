# Lint

You MUST use these linting and quality tools where applicable:

- [ruff](https://github.com/astral-sh/ruff)
- [shellcheck](https://github.com/koalaman/shellcheck)
- [hadolint](https://github.com/hadolint/hadolint)

## Repository Lint Rules

You MUST apply these repo-wide rules when you add, move, or review files:

- Keep broad folders shallow when that helps readability. Direct children SHOULD stay at 12 or fewer items per folder.
- Treat structural hubs such as `roles/`, `cli/`, `tests/unit/plugins/filter`, `tests/unit/roles`, `inventories/bundles/servers`, `inventories/bundles/workstations`, `plugins/filter`, `plugins/lookup`, `group_vars/all`, and `.github/workflows` as intentional exceptions when they are used to organize the tree.
- You SHOULD prefer smaller, more focused folders over dumping many unrelated files into one directory.

For refactoring guidance, see [Refactoring](../../flow/refactoring.md).
