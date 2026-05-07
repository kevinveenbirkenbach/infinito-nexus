# Lookup Plugin Tests 🔎

Integration tests for the custom Ansible lookup plugins under `plugins/lookup/`: config-path validation against role schemas and runtime caching performance.

Tests in this directory MUST only cover lookup-plugin behavior (schema validation of `lookup('config', …)` paths, caching semantics, performance smoke). Pure unit tests for a single lookup plugin's return values MUST live under `tests/unit/plugins/lookup/`.

`config/` holds the `lookup('config', …)` path-validation suite, split SRP-style:
`test_literal_paths.py`, `test_variable_paths.py`, `test_wildcard_paths.py`,
`test_role_local_paths.py`. All four share a single project scan via
`_scan.get_scan` (`functools.lru_cache`); validation helpers live in `_validate.py`.

For framework, directory layout, and `make test-integration` usage see [integration.md](../../../docs/contributing/actions/testing/integration.md).
