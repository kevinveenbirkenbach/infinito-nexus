# Contribution Flow 🔀

This repository uses a strict fork-first workflow. You MUST NOT commit directly to `main`. You MUST do all work in your own fork and MUST open Pull Requests from your fork back to the main repository.

These rules are enforced via branch protection. See [branch.md](security/branch.md) for the full policy.

Why this matters: `main` MUST stay stable, shared CI resources are limited, and broken experimental work MUST NOT run in the main repository.

## Repository Configuration 🧩

Before running workflows you MUST configure the required secrets and credentials for the repository. This includes GHCR authentication for pushing and publishing container images. See [ghcr.md](security/ghcr.md) for the full setup guide.

## Step-by-Step Flow 🪜

1. Create or update your fork.
2. Create a branch in your fork with the right prefix. See [branch.md](branch.md).
3. Make one focused change at a time.
4. Run the relevant local checks. See [testing.md](testing.md).
5. Push the branch to your fork.
6. Wait until the CI in your fork is green. See [pull-request.md](pull-request.md) for required CI scope.
7. Open a [Pull Request](pull-request.md).
8. Address review feedback in your fork. See [review.md](review.md).

## Discussion 💬

Questions and discussion about the contribution workflow MAY be raised in the [Infinito Nexus Hub](https://hub.infinito.nexus). A dedicated thread on forking and contributing is available [here](https://s.infinito.nexus/forking).
