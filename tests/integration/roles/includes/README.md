# Include/Import Existence Tests 📎

Integration tests that enforce every `include_tasks` / `import_tasks` / `include_role` / `import_role` target referenced from role tasks (and other project YAML) resolves to an existing file.

Tests in this directory MUST only cover target-existence rules for `include_*` / `import_*` directives. Rules about the block-level `when:` wrapping those includes MUST live under [`../when/`](../when/); rules about `run_once_<role>` flag inclusion MUST live under [`../run_once/`](../run_once/).

For framework, directory layout, and `make test-integration` usage see [integration.md](../../../../docs/contributing/actions/testing/integration.md).
