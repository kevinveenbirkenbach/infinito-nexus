# Role Structure Tests 📚

Integration tests that enforce structural invariants of every role under `roles/`: folder-name conventions, required `meta/main.yml`, dependency graph (no self-, no circular, no unnecessary dependencies), and `include_tasks` / `import_tasks` target existence.

Tests in this directory MUST only cover role-level structural and metadata rules. Tests tied to `application_id` identity MUST live under `tests/integration/application_id/`, and compose- or handler-specific checks MUST live in their respective topical clusters.

For framework, directory layout, and `make test-integration` usage see [integration.md](../../../docs/contributing/actions/testing/integration.md).
