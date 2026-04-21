# When-Guard Tests 🚦

Integration tests for block-level `when:` hygiene across `roles/*/tasks/**`: max-three-task guard blocks, no duplicated when-conditions across tasks, and the pure-guarded-include pattern for role inclusion.

Tests in this directory MUST only cover rules about block-level `when:` semantics and guard-block shape. `run_once_<role>` flag lifecycle checks MUST live under [`../run_once/`](../run_once/); rules about `include_tasks` / `import_tasks` target existence MUST live under [`../includes/`](../includes/).

For framework, directory layout, and `make test-integration` usage see [integration.md](../../../../docs/contributing/actions/testing/integration.md).
