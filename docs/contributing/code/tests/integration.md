# Integration Tests

This page is the SPOT for integration testing requirements, framework, and structure.
Run integration tests with `make test-integration`.

## Framework

- You MUST use Python `unittest` as the test framework.
- Tests MUST live under `tests/integration/`.
- Mirror the source tree structure used for unit tests.

## When to Write

- You MUST add or update integration tests for every `*.py` file you touch when the change affects behavior across module or runtime boundaries.
- Write an integration test when the behavior you are verifying depends on two or more components working together — for example, a lookup plugin reading from real `group_vars` or a filter interacting with an Ansible variable structure.

## Requirements

- You MUST NOT mock collaborators that are part of the integration boundary being tested. The point is to verify real interaction.
- You MUST NOT write tests that only assert a file contains a string.
- You MUST NOT write tests only for non-executable files such as `.yml` or `.j2`. Test the behavior that consumes them.
- You SHOULD keep each test focused on one integration boundary.
- You SHOULD test realistic inputs that match what Ansible would pass at runtime.
- You MAY use `unittest.mock` to stub out external services or filesystem state that is genuinely outside the integration scope.

## How to Create

1. Identify the integration boundary (e.g. lookup plugin + `group_vars` variable loading).
2. Create the matching test file under `tests/integration/` if it does not exist.
3. Subclass `unittest.TestCase`.
4. Use realistic inputs. Build hypotheses about cross-component behavior before writing assertions.
5. Run `make test-integration` and verify all tests pass.

## Running Specific Tests

Use `TEST_PATTERN` to scope the test run to a single file or a glob:

```bash
# Run a single integration test file
TEST_PATTERN=test_my_module.py make test-integration

# Run all files matching a prefix
TEST_PATTERN=test_applications*.py make test-integration
```
