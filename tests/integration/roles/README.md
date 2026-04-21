# Role Structure Tests 📚

Integration tests that enforce structural invariants of every role under `roles/`: folder-name conventions and `include_tasks` / `import_tasks` target existence.

Tests in this directory MUST only cover role-level structural rules. `meta/main.yml` presence and field checks MUST live under [`meta/`](meta/). Dependency-graph checks (self-, circular, unnecessary dependencies, `run_after`) MUST live under [`dependencies/`](dependencies/). Application-specific role rules (web-app README, `applications[...]` / `group_names` usage, `application_id` identity) MUST live under [`applications/`](applications/). `run_once_<role>` flag lifecycle checks MUST live under [`run_once/`](run_once/). Compose- or handler-specific checks MUST live in their respective topical clusters.

For framework, directory layout, and `make test-integration` usage see [integration.md](../../../docs/contributing/actions/testing/integration.md).
