[Back to Frameworks](README.md)

# Makefile

Use this page for rules that shape the repository's `Makefile`.

The `Makefile` is the human-facing command surface for the repo. It MUST expose stable targets that people and CI are meant to run directly.

## Target Design

- You MUST keep public targets stable, named clearly, and documented.
- You MUST NOT add a target unless a human operator or CI should run it directly.
- You MUST keep helper-only logic, plumbing, and intermediate steps in `scripts/` or other implementation files.
- You SHOULD prefer targets that compose smaller scripts instead of embedding large shell fragments in the `Makefile`.
- You MUST keep the command surface small enough that contributors can discover the obvious path quickly.

## Repository Entry Points

The architecture overview treats `Makefile` and `scripts/` as the supported command entry points. The command groups themselves are documented here:

- [Development Environment Setup](../../environment/setup.md)
- [Docker and Runtime Commands](../../tools/docker.md)
- [Testing and Validation](../../development/testing.md)

For the broader architecture context, see [Repository Architecture](../architecture.md).
