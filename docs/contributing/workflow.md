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
2. Create a branch in your fork with the right prefix.
3. Make one focused change at a time.
4. Run the relevant local checks.
5. Push the branch to your fork.
6. Wait until the CI in your fork is green.
7. Open a Pull Request.
8. Address review feedback in your fork.

## Branch Prefixes

Use these prefixes for branch names:

| Prefix | When to use it | Example |
|---|---|---|
| `feature` | New functionality or improvements. | `feature/add-matomo-integration` |
| `fix` | Bugfixes and other corrective changes. | `fix/login-redirect` |
| `agent` | Changes to agent instruction files such as `AGENTS.md` or files in `docs/agents/`. | `agent/debugging-guidance` |
| `documentation` | Pure documentation-only changes. | `documentation/docker-guide` |

The pull-request workflow validates the branch prefix against the touched file scope and fails the job when they do not match.

More information about the contribution workflow is available [here](https://s.infinito.nexus/forking).
