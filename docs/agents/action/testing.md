# Testing

## Test Changes

- After every change to a test file, you MUST run the corresponding validation command before continuing with any further action. Use the suite-selection rules in [Testing and Validation](../../contributing/flow/testing.md).
- You MUST NOT run more than one unit test command at the same time. Unit tests MUST be executed serially, never in parallel.
- If a new test is created or an existing test has been changed since the last test run, you MUST rerun it after every subsequent action until it passes.
- If the last test run for a test failed, you MUST rerun it after every change until it succeeds.

## Commits

- `make test` is enforced automatically by the pre-commit hook before every commit for changes that include at least one file that is not `.md`, `.rst`, or `.txt`. You do NOT need to run it manually.
- For markdown/reStructuredText/text-only changes, the hook skips `make test` automatically.
- If the pre-commit hook warns about a staged file or its role, you MUST ask whether to fix that warning before you continue.
- Keep the follow-up limited to the roles touched by staged files so the change stays focused.

## On Failure
- If that validation fails, you MUST run `make clean` and rerun it.
- If the failure says `service "infinito" is not running`, restart the stack with [Development Environment Setup](../../contributing/environment/setup.md) and retry the validation.
