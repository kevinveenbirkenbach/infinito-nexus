# Lookup Plugin Tests 🔎

Integration tests for the custom Ansible lookup plugins under `plugins/lookup/`: config-path validation against role schemas and runtime caching performance.

Tests in this directory MUST only cover lookup-plugin behavior (schema validation of `lookup('config', …)` paths, caching semantics, performance smoke). Pure unit tests for a single lookup plugin's return values MUST live under `tests/unit/plugins/lookup/`.

For framework, directory layout, and `make test-integration` usage see [integration.md](../../../docs/contributing/actions/testing/integration.md).
