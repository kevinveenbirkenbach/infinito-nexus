# GitHub Workflow Helpers

This is the SPOT for GitHub workflow helper scripts under `scripts/github/`.
These helpers are called from `.github/workflows/`.
For the repository Make target index, see [docs/contributing/tools/makefile.md](../../docs/contributing/tools/makefile.md).

## Entry Points

| Script | What it does | Used by |
|---|---|---|
| `cancel_deleted_branch_runs.sh` | Cancels active workflow runs for a deleted branch. | `.github/workflows/delete-branch.yml` |
| `cancel_pull_request_runs.sh` | Cancels active workflow runs for a closed pull request. | `.github/workflows/cancel-pull-request-runs.yml` |
