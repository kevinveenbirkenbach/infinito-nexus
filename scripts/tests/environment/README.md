# Environment Test Suite

This directory contains the modular environment test suite for Infinito.Nexus.
It validates the full local development flow from a clean state.

The entry point is [00_orchestrator.sh](00_orchestrator.sh).

## Structure

| File | Purpose |
|---|---|
| [00_orchestrator.sh](00_orchestrator.sh) | Runs all numbered steps in order |
| [01_install.sh](01_install.sh) | Installs package prerequisites and repository dependencies |
| [02_system.sh](02_system.sh) | Shows disk usage and purges cached state |
| [03_build.sh](03_build.sh) | Builds the local Docker image |
| [04_git.sh](04_git.sh) | Bootstraps a temporary Git repository for CI snapshot-based runs |
| [05_bootstrap.sh](05_bootstrap.sh) | Bootstraps the development environment and starts the stack |
| [06_test.sh](06_test.sh) | Runs the full validation suite |
| [07_deploy_minimal.sh](07_deploy_minimal.sh) | Deploys on minimal hardware with service exclusion |
| [08_deploy_performance.sh](08_deploy_performance.sh) | Deploys the full application set on performance hardware |
| [09_deploy_reuse.sh](09_deploy_reuse.sh) | Redeploys reusing existing inventory and packages |
| [10_commit.sh](10_commit.sh) | Validates pre-commit hook enforcement and `--no-verify` bypass |
| [11_teardown.sh](11_teardown.sh) | Shuts down the stack and reverses environment changes |
| [lib.sh](lib.sh) | Shared variables and helper functions |

## Usage

Run the full suite via the entry point:

```bash
bash scripts/tests/environment/00_orchestrator.sh
```

For documentation on the overall development workflow, see the [Administration Guide](../../../docs/guides/administration.md).
