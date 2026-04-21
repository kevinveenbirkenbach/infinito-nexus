# Role Spot Tests 🎯

Integration spot-checks pinned to specific roles — narrow assertions that catch regressions in a single role's templates, vars, or task layout.

Tests in this directory MUST only cover role-specific invariants that do not generalize across roles. Use the filename `test_<role>_<aspect>.py`. Rules that should hold across every role MUST live in the corresponding topical cluster (e.g., [`config/`](../config/), [`compose/`](../compose/), [`handlers/`](../handlers/)).

For framework, directory layout, and `make test-integration` usage see [integration.md](../../../docs/contributing/actions/testing/integration.md).
