[Back to AGENTS hub](../../AGENTS.md)

# Committing

- Run `make test` as the standard combined validation from [Testing and Validation](../../docs/contributing/testing.md) before every commit whenever the staged change includes at least one file that is not `.md` or `.rst`, unless you are explicitly instructed not to.
- If that validation fails, run `make clean-sudo` and rerun it.
- If the failure says `service "infinito" is not running`, restart the stack with [Development Environment Setup](../../docs/contributing/setup.md) and retry the validation.
- Skip the standard validation only for markdown/reStructuredText-only changes unless you are explicitly instructed to run it.
- Commit only after all required checks pass.

## Warnings

- If the standard validation warns about a staged file or its role, ask whether to fix that warning before you continue.
- Keep the follow-up limited to the roles touched by staged files so the change stays focused.
