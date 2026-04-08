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
| [04_bootstrap.sh](04_bootstrap.sh) | Bootstraps the development environment and starts the stack |
| [05_test.sh](05_test.sh) | Runs the full validation suite |
| [06_deploy_minimal.sh](06_deploy_minimal.sh) | Deploys on minimal hardware with service exclusion |
| [07_deploy_performance.sh](07_deploy_performance.sh) | Deploys the full application set on performance hardware |
| [08_deploy_reuse.sh](08_deploy_reuse.sh) | Redeploys reusing existing inventory and packages |
| [09_commit.sh](09_commit.sh) | Validates pre-commit hook enforcement and `--no-verify` bypass |
| [10_teardown.sh](10_teardown.sh) | Shuts down the stack and reverses environment changes |
| [lib.sh](lib.sh) | Shared variables and helper functions |

## Usage

Run the full suite via the entry point:

```bash
bash scripts/tests/environment/00_orchestrator.sh
```

Or run individual steps directly:

```bash
bash scripts/tests/environment/05_test.sh
```

For documentation on the overall development workflow, see the [Administration Guide](../../../docs/guides/administration.md).
