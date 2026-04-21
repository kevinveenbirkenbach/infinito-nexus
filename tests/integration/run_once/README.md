# Run-Once Flag Tests 🏁

Integration tests for the `run_once_<role_name>` fact pattern: flag suffixes MUST match their role folder name, flags MUST be defined before use, and inclusion of `utils/once/flag.yml` MUST follow the schema.

Tests in this directory MUST only cover `run_once_*` flags and their lifecycle. Tests for generic fact overrides, task includes, or block structure MUST live elsewhere under `tests/integration/`.

For framework, directory layout, and `make test-integration` usage see [integration.md](../../../docs/contributing/actions/testing/integration.md).
