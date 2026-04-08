# Committing

- You MUST commit only after all required checks pass.
- You MUST NOT commit automatically without explicit confirmation from the user. ALWAYS ask before committing.
- `make test` is run automatically by pre-commit before every commit when staged changes include at least one file that is not `.md`, `.rst`, or `.txt`. You do NOT need to run it manually — the pre-commit hook enforces it.
- If the pre-commit hook fails, fix the underlying issue and retry the commit. Do NOT bypass hooks with `--no-verify` unless the user explicitly instructs you to commit without running tests.
- For markdown/reStructuredText/text-only changes, pre-commit skips `make test` automatically. You MUST NOT run it manually either.
