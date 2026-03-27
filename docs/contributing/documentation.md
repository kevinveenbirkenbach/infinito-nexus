[Back to CONTRIBUTING hub](../../CONTRIBUTING.md)

# Documentation

All project documentation should be reachable at [docs.infinito.nexus](https://docs.infinito.nexus/).

## Documentation and Comments

- Keep core information inside the repository, either in code or in `.md` files.
- Use `.md` files for commands, workflows, setup, and contributor guidance.
- Do not use `.md` files to describe implementation logic that is already visible in the code.
- Write code so it is logical and self-explanatory and usually does not need comments.
- Add code comments only when an exception, edge case, or surprising decision would otherwise confuse readers.
- Use comments to explain why something is unusual, not to restate what obvious code already does.

## Semantics and Writing

- Keep code and comments in English.
- Fix nearby wording and semantic issues when you touch a file, and correct obvious nearby issues proactively in the same pass.

## Documentation Structure

- Prefer `README.md` for directory-level documentation when a human-facing entry point already exists.
- If a documentation directory does not already have a `README.md`, add an `index.rst` where it helps automated docs generation.
- Keep Sphinx-friendly directory indexes up to date so the published documentation can include new content without extra wiring.
