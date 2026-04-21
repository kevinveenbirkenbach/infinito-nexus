# Application ID Tests 🆔

Integration tests that enforce the contract between a role's folder name, its `application_id` in `vars/main.yml`, and the invokability classification from `plugins/filter/invokable_paths.py`.

Tests in this directory MUST only cover `application_id` rules (presence, deprecation, prefix-to-role-name consistency). Cross-cutting role validation that is not tied to `application_id` MUST live elsewhere under `tests/integration/`.

For framework, directory layout, and `make test-integration` usage see [integration.md](../../../docs/contributing/actions/testing/integration.md).
