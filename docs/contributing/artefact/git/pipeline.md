# Continuous Integration 🔄

This document describes the CI pipeline structure, entry points, and gates used in Infinito.Nexus. For the catalog of every workflow file (description, triggers, inputs) see [actions.md](../../tools/github/actions.md).

## Overview 🗺️

CI is triggered automatically on pull request events and push to `latest`. The pipeline is composed of reusable workflow files under [.github/workflows/](../../../../.github/workflows/). The central coordinator is [ci-orchestrator.yml](../../../../.github/workflows/ci-orchestrator.yml), which is called by the entry workflows.

## Entry Points 🚪

| Trigger | Workflow | Description |
|---|---|---|
| Pull request (opened, synchronize, reopened, ready\_for\_review) | [entry-pull-request-change.yml](../../../../.github/workflows/entry-pull-request-change.yml) | Detects PR scope and conditionally runs the full orchestrator |
| Push to `latest` | [entry-push-latest.yml](../../../../.github/workflows/entry-push-latest.yml) | Runs the full orchestrator on the main branch |
| Manual dispatch | [entry-manual.yml](../../../../.github/workflows/entry-manual.yml) | Allows triggering CI for a specific role or whitelist |

## PR Scope Detection 🔎

Before the full pipeline runs, CI detects the scope of the PR based on the changed files and the branch prefix (see [branch.md](branch.md)).

- Documentation-only and agent-only PRs MUST pass a lightweight gate without running the full orchestrator.
- All other scopes MUST run the full [ci-orchestrator.yml](../../../../.github/workflows/ci-orchestrator.yml).
- The branch prefix MUST match the detected scope, otherwise the `validate-pr-branch-prefix` job fails.

## Pipeline Stages 🏗️

The orchestrator runs the following stages in order:

### 1. Fork Prerequisites ⏳

For fork PRs, CI waits for privileged images to be built by the `pull_request_target` event before proceeding. This ensures untrusted code never runs with elevated permissions.

### 2. Security 🛡️

- [security-codeql.yml](../../../../.github/workflows/security-codeql.yml): Static analysis via GitHub CodeQL.

### 3. Linting 🧹

All linting jobs run in parallel:

- [lint-ansible.yml](../../../../.github/workflows/lint-ansible.yml)
- [lint-docker.yml](../../../../.github/workflows/lint-docker.yml)
- [lint-python.yml](../../../../.github/workflows/lint-python.yml)
- [lint-shell.yml](../../../../.github/workflows/lint-shell.yml)

All four MUST pass the `lint-gate` before the pipeline continues.

### 4. CI Image Build 🐳

[images-build-ci.yml](../../../../.github/workflows/images-build-ci.yml) builds Docker images for the target distributions (`arch`, `debian`, `ubuntu`, `fedora`, `centos`). These images are used by all subsequent test jobs.

### 5. Code Tests 🧪

Run in parallel after images are available:

- [test-code-integration.yml](../../../../.github/workflows/test-code-integration.yml)
- [test-code-lint.yml](../../../../.github/workflows/test-code-lint.yml)
- [test-code-unit.yml](../../../../.github/workflows/test-code-unit.yml)

All three MUST pass the `test-code-gate`.

### 6. Code Quality Gate 🚦

The `code-quality-gate` requires linting, code tests, and security checks to all pass before deploy tests are triggered.

### 7. DNS Tests 🌐

[test-dns.yml](../../../../.github/workflows/test-dns.yml) validates DNS configuration across all target distributions.

### 8. Image Mirroring 🪞

[images-mirror-missing.yml](../../../../.github/workflows/images-mirror-missing.yml) mirrors any missing upstream images in parallel with the DNS tests so later deploy jobs pull from GHCR instead of Docker Hub, MCR, or other external registries. This shields CI from upstream rate limits, geo-blocking, and transient registry outages.

Fork PRs cannot publish mirror packages directly, so their untrusted runs wait for the trusted mirror producer before continuing. See [mirror.md](../image/mirror.md) for the mirroring architecture and naming convention.

GHCR publication uses the workflow `GITHUB_TOKEN`; optional Docker Hub secrets are used only to reduce source-side Docker Hub rate limits while mirroring. See [authentication.md](../../tools/ghcr/authentication.md).

### 9. Deploy Tests 🚀

Run in parallel after DNS and mirroring:

- [test-deploy-server.yml](../../../../.github/workflows/test-deploy-server.yml): Server and `web-*` roles.
- [test-deploy-universal.yml](../../../../.github/workflows/test-deploy-universal.yml): Shared system roles.
- [test-deploy-workstation.yml](../../../../.github/workflows/test-deploy-workstation.yml): Workstation and `desk-*` roles.

### 10. Installation Tests 📦

Run in parallel after the code quality gate:

- [test-install-make.yml](../../../../.github/workflows/test-install-make.yml)
- [test-install-pkgmgr.yml](../../../../.github/workflows/test-install-pkgmgr.yml)

Both MUST pass the `test-install-gate`.

### 11. Development Environment 🛠️

[test-environment.yml](../../../../.github/workflows/test-environment.yml) validates the development environment setup.

### 12. Done 🏁

The final `done` job aggregates all deploy, install, and development gates. CI is considered green only when this job succeeds.

## Concurrency 🔀

- PR pipelines use `cancel-in-progress: true` so only the newest run per PR and event type is active.
- The orchestrator uses `cancel-in-progress: false` to avoid interrupting long-running deploy tests mid-flight.
- The push entry workflow (`entry-push-latest.yml`) defaults to `cancel-in-progress: true` but respects the
  repository variable `CI_CANCEL_IN_PROGRESS`. Set it to `false` under
  **Settings → Secrets and variables → Actions → Variables** to prevent in-progress runs from being cancelled
  on the `main` / feature branches. Any other value (or no value) keeps the default cancel behaviour.

See [configuration.md](../../tools/github/branch/configuration.md) for all repository variables that control CI behaviour.

## Fork PRs 🍴

Fork PRs run under the `pull_request` event without write permissions. Privileged steps (image builds, package writes) run via `pull_request_target` after a maintainer review. The fork CI waits for those privileged images before proceeding. See [pull-request.md](pull-request.md) for the contributor-facing fork workflow.
