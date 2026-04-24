# Application ID Tests 🆔

Integration tests that enforce the contract between a role's folder name, its `application_id` in `vars/main.yml`, and the invokability classification from `plugins/filter/invokable_paths.py`.

Tests in this directory MUST only cover `application_id` rules (presence, deprecation, prefix-to-role-name consistency). Generic application-role checks (web-app README, `applications[...]` / `group_names` usage) MUST live one level up under [`../`](../).

For framework, directory layout, and `make test-integration` usage see [integration.md](../../../../../docs/contributing/actions/testing/integration.md).
