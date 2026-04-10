# Lint 🔍

You MUST use these linting and quality tools where applicable:

- [ruff](https://github.com/astral-sh/ruff)
- [shellcheck](https://github.com/koalaman/shellcheck)
- [hadolint](https://github.com/hadolint/hadolint)

## Repository Lint Rules 📏

You MUST apply these repo-wide rules when you add, move, or review files:

- Keep broad folders shallow when that helps readability. Direct children SHOULD stay at 12 or fewer items per folder.
- Treat structural hubs such as `roles/`, `cli/`, `tests/unit/plugins/filter`, `tests/unit/roles`, `inventories/bundles/servers`, `inventories/bundles/workstations`, `plugins/filter`, `plugins/lookup`, `group_vars/all`, and `.github/workflows` as intentional exceptions when they are used to organize the tree.
- You SHOULD prefer smaller, more focused folders over dumping many unrelated files into one directory.

For refactoring guidance, see [Refactoring](../flow/refactoring.md).

## Suppression Comments 🚫

Some lint checks can be suppressed on a per-item basis using inline comments.
You MUST use these only when the check genuinely does not apply.
You MUST NOT use them to silence legitimate issues.

| Comment | Placement | Affected test | Effect |
|---|---|---|---|
| `# nocheck: docker-version` | Line directly above `version:` in `config/main.yml` | [test_image_versions.py](../../../tests/lint/docker/test_image_versions.py) | Skips automated version-update checks and PR creation for that image |
| `# noqa: shared` | Line directly above `shared:` in `config/main.yml` | [test_service_shared_consistency.py](../../../tests/lint/ansible/test_service_shared_consistency.py) | Skips shared-consistency validation for that service |
| `# run_once_<key>: deactivated` | Inside the task file, on the task entry | [test_run_once_tags.py](../../../tests/lint/ansible/test_run_once_tags.py) | Suppresses the run-once tag warning for that specific task key |

## Running Specific Lint Tests 🏃

Use `TEST_PATTERN` to scope the lint test run to a single file:

```bash
# Run lint tests for a specific file
TEST_PATTERN=test_my_role.py make test-lint
```
