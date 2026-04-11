# GitHub Workflow Helpers 🔧

This is the SPOT for GitHub workflow helper scripts under `scripts/github/`.
These helpers are called from `.github/workflows/`.
For the repository Make target index, see [make.md](../../docs/contributing/tools/make.md).

## Entry Points 📋

| Script | What it does | Used by |
|---|---|---|
| `cancel_deleted_branch_runs.sh` | Cancels active workflow runs for a deleted branch. | `.github/workflows/delete-branch.yml` |
| `cancel_pull_request_runs.sh` | Cancels active workflow runs for a closed pull request. | `.github/workflows/cancel-pull-request-runs.yml` |
| `check_git_changes.sh` | Emits a `changed=true/false` workflow output based on `git diff`. | `.github/workflows/update.yml` |
| `install_update_python.sh` | Installs Python dependencies needed by the automated update workflows. | `.github/workflows/update.yml` |
| `open_update_pr.sh` | Commits update changes, pushes the branch, and creates or refreshes the matching Pull Request. | `.github/workflows/update.yml` |
| `update_docker_image_versions.sh` | Runs the Docker image version updater CLI from GitHub Actions. | `.github/workflows/update.yml` |
