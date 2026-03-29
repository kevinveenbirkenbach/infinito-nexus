# Contribution Flow

This repository uses a strict fork-first workflow.

- You MUST NOT commit directly to `main`.
- You MUST do all work in your own fork.
- You MUST open Pull Requests from your fork back to the main repository.

Why this matters:

- `main` MUST stay stable.
- Shared CI resources are limited.
- Broken experimental work MUST NOT run in the main repository.

## Step-by-Step Flow

1. Create or update your fork.
2. Create a branch in your fork with the right prefix.
3. Make one focused change at a time.
4. Run the relevant local checks.
5. Push the branch to your fork.
6. Wait until the CI in your fork is green.
7. Open a Pull Request.
8. Address review feedback in your fork.

## Branch Prefixes

Branch names MUST follow the conventions defined in [branch.md](branch.md).

Questions and discussion about the contribution workflow MAY be raised in the [Infinito Nexus Hub](https://hub.infinito.nexus). A dedicated thread on forking and contributing is available [here](https://s.infinito.nexus/forking).
