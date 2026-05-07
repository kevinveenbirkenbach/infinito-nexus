# Ansible Variable Lints 🪪

Lint tests that enforce variable-lifecycle invariants across the Ansible tree: every name a role declares MUST be consumed somewhere, and every name a role passes MUST be referenced by the play / template stack that receives it.

Tests in this directory MUST only cover variable definition / consumption checks. Two orthogonal scopes live here:

- `test_role_and_group_vars_used.py` scans top-level keys of `roles/<role>/{vars,defaults}/main.yml` and `group_vars/**/*.yml` against every project `.yml` / `.yaml` / `.j2` file. The suppression rule key is `unused-var` (see [suppression.md](../../../../docs/contributing/actions/testing/suppression.md)).
- `test_vars_usage_in_yaml.py` scans task-level `vars:` blocks against the same consumer set. The two scanners never overlap because their declaration shapes differ.

Both tests route every read through the project caches (`utils.cache.files`, `utils.cache.yaml`); contributors adding a new variable scanner MUST do the same instead of calling `yaml.safe_load*` or `open()` directly.

For framework, directory layout, and `make test-lint` usage see [lint.md](../../../../docs/contributing/actions/testing/lint.md).
