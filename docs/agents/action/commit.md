# Committing

- You MUST commit only after all required checks pass.
- You MUST NOT commit automatically without explicit confirmation from the user. ALWAYS ask before committing.
- `make test` is run automatically by pre-commit before every commit when staged changes include at least one file that is not `.md`, `.rst`, or `.txt`. You do NOT need to run it manually — the pre-commit hook enforces it.
- If the pre-commit hook fails, fix the underlying issue and retry the commit.
- You MUST NOT use `--no-verify` unless the user gives a direct, unambiguous instruction to bypass the hook (e.g. "skip the hook", "bypass pre-commit").
- Generic commit requests — such as "commit the changes", "commit", or any equivalent in any language — do NOT qualify. When in doubt, do NOT use `--no-verify`.
- For markdown/reStructuredText/text-only changes, pre-commit skips `make test` automatically. You MUST NOT run it manually either.
