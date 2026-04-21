# Repository Linting Tests 🧹

Integration tests that enforce cross-cutting repository hygiene: YAML syntax, Python shebangs, shell-script executability, safe `sed` usage, packaging-metadata consistency, `unittest` imports, and filename conventions.

Tests in this directory MUST only cover repository-wide style and structural rules that do not belong to a single subsystem. Semantic checks on roles, compose files, or Ansible tasks MUST live in their respective topical clusters.

For framework, directory layout, and `make test-integration` usage see [integration.md](../../../docs/contributing/actions/testing/integration.md).
