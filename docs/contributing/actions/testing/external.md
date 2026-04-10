# External Tests 🌐

This page is the SPOT for tests that depend on live third-party systems such as
Docker Hub, GHCR, or other external services.
Run external tests with `make test-external`.

## Goal 🎯

- You MUST use external tests only when the behavior depends on a live third-party
  system and a hermetic unit, lint, or integration test would not verify the
  real condition.
- You MUST keep external tests outside the default `make test` flow so normal
  validation stays reproducible without third-party network access.
- You SHOULD keep external tests focused, advisory, and easy to run on demand.

## Location 📁

- External tests MUST live under `tests/external/`.
- You SHOULD group them by dependency family such as `tests/external/docker/`
  or `tests/external/github/` when more than one test exists.
- Every external test directory MUST contain `__init__.py` so repository-wide
  test structure checks keep passing.

## Requirements 📋

- You MUST document in the test file why the check is external and what live
  dependency it contacts.
- You MUST NOT move an external test into `tests/lint/`, `tests/unit/`, or
  `tests/integration/` just for convenience when it still depends on live
  third-party state.
- External tests MAY emit warnings instead of hard failures when the goal is
  advisory freshness reporting rather than merge-blocking correctness.
- You SHOULD keep network traffic narrow and query each external dependency only
  as much as needed for a meaningful result.

## Running 🏃

Use the dedicated make target:

```bash
make test-external
```

To scope the run to one file:

```bash
TEST_PATTERN=test_image_versions.py make test-external
```

## CI Workflow 🤖

The dedicated workflow lives at `.github/workflows/test-code-external.yml`.
It MAY be triggered manually and is intentionally separate from the default
combined validation flow.
