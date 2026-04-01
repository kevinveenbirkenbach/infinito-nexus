# Testing

## Test Changes

- After every change to a test file, you MUST run the specialized test for that file using `TEST_PATTERN` before continuing with any further action. See [Unit Tests](../../contributing/code/tests/unit.md), [Integration Tests](../../contributing/code/tests/integration.md), and [Lint Tests](../../contributing/code/tests/lint.md) for examples.
- If a new test is created or an existing test has been changed since the last test run, you MUST rerun it after every subsequent action until it passes.
- If the last test run for a test failed, you MUST rerun it after every change until it succeeds.

## Commits

- You MUST run the full `make test` (which executes lint, unit, integration, and deploy checks) before every commit whenever the staged change includes at least one file that is not `.md` or `.rst`, unless you are explicitly instructed not to.
- You MUST skip the standard validation only for markdown/reStructuredText-only changes unless you are explicitly instructed to run it.
- If the standard validation warns about a staged file or its role, you MUST ask whether to fix that warning before you continue.
- Keep the follow-up limited to the roles touched by staged files so the change stays focused.

## On Failure
- If that validation fails, you MUST run `make clean` and rerun it.
- If the failure says `service "infinito" is not running`, restart the stack with [Development Environment Setup](../../contributing/environment/setup.md) and retry the validation.
