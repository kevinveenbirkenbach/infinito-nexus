[Back to CONTRIBUTING hub](../../CONTRIBUTING.md)

# Contribution Flow

This repository uses a strict fork-first workflow.

- Do not commit directly to `main`.
- Do all work in your own fork.
- Open Pull Requests from your fork back to the main repository.

Why this matters:

- `main` should stay stable.
- Shared CI resources are limited.
- Broken experimental work should not run in the main repository.

## Step-by-Step Flow

1. Create or update your fork.
2. Create a feature branch in your fork.
3. Make one focused change at a time.
4. Run the relevant local checks.
5. Push the branch to your fork.
6. Wait until the CI in your fork is green.
7. Open a Pull Request.
8. Address review feedback in your fork.

Use the prefix `feature` for feature branches and `fix` for bugfixes and other fixes, for example `feature/my-change` or `fix/login-bug`.

More information about the contribution workflow is available [here](https://s.infinito.nexus/forking).

