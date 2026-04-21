# Role `meta/main.yml` Tests 🧾

Integration tests that enforce invariants of each role's `meta/main.yml`: the file MUST exist for every role under `roles/`, and `galaxy_info` MUST carry the fields the Sphinx generator expects (non-empty `description`, no `None` values).

Tests in this directory MUST only cover `meta/main.yml` presence and field shape. Tests about role dependencies declared in that file (`dependencies:`, `galaxy_info.run_after`) MUST live under [`../dependencies/`](../dependencies/).

For framework, directory layout, and `make test-integration` usage see [integration.md](../../../../docs/contributing/actions/testing/integration.md).
