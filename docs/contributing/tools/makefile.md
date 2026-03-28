[Back to CONTRIBUTING hub](../../../CONTRIBUTING.md)

# Makefile Commands

Use these commands from the repository root. This is the SPOT for `make` targets in Infinito Nexus.
Use the dedicated script READMEs for the underlying shell helpers, and use the development/testing guides for deeper workflow details.

## Image Builds

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Build | `make build` | Builds the local image for the active `INFINITO_DISTRO`. | Use this after Dockerfile changes or whenever you want a fresh local image. |
| Build if missing | `make build-missing` | Builds the image only when it is not already present locally. | Use this for a quick local check when you do not want to rebuild unnecessarily. |
| No-cache build | `make build-no-cache` | Rebuilds the image without Docker cache. | Use this when cache reuse might hide a change or when you are debugging the build. |
| No-cache all distros | `make build-no-cache-all` | Rebuilds the no-cache image for every distro in `DISTROS`. | Use this for release-level validation or when you need to verify all distro variants. |
| Build dependency image | `make build-dependency` | Pulls the `pkgmgr` base image used by the build. | Use this when you want to refresh the base image or debug build inputs. |
| Cleanup CI images | `make build-cleanup` | Removes Docker images created for CI-style build workflows. | Use this when local disk usage grows or old CI images accumulate. |
| Regenerate Docker ignore | `make dockerignore` | Regenerates `.dockerignore` from `.gitignore`. | Use this when the Docker ignore file needs to be refreshed. |

## Install

| Category | Command | What it does | When to use it |
|---|---|---|---|
| System Python prerequisites | `make install-system-python` | Installs the system Python prerequisites. | Use this when the host is missing the Python base packages. |
| Virtual environment | `make install-venv` | Creates the virtual environment. | Use this when you need the repository Python environment. |
| Python tooling | `make install-python` | Installs the Python tooling. | Use this when you need the Python toolchain after creating the virtual environment. |
| Ansible dependencies | `make install-ansible` | Installs the Ansible dependencies. | Use this when you changed Ansible-related code or need the Ansible collections. |
| Lint dependencies | `make install-lint` | Installs lint-related tooling. | Use this when you only need the lint stack. |
| Full install | `make install` | Installs the repository tooling needed for development and tests. | Use this on a fresh machine or before validation. |

## Environment Setup

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Environment bootstrap | `make environment-bootstrap` | Runs the local bootstrap sequence for WSL2, lint tooling, AppArmor, DNS, and IPv6. | Use this when you want to prepare a fresh development host. |
| Environment teardown | `make environment-teardown` | Reverses the local bootstrap sequence. | Use this when you want to restore host settings. |
| Enable WSL2 systemd | `make wsl2-systemd-check` | Ensures WSL2 systemd support is configured. | Use this before WSL2-specific setup that depends on systemd. |
| Set up DNS on WSL2 | `make wsl2-dns-setup` | Configures DNS for WSL2. | Use this when you are working in WSL2 and need local DNS routing. |
| Configure DNS | `make dns-setup` | Configures DNS on the current host. | Use this for Linux host DNS setup. |
| Remove DNS | `make dns-remove` | Removes the DNS configuration. | Use this to clean up the DNS setup. |
| Trust CA on Windows | `make wsl2-trust-windows` | Imports the local CA and updates hosts entries from WSL2. | Use this when you need Windows trust-store updates from WSL2. |
| Trust local CA | `make trust-ca` | Trusts the local CA on Linux and WSL2. | Use this after the CA or host entries change. |
| Disable IPv6 | `make disable-ipv6` | Disables IPv6 for local development. | Use this when a workflow needs IPv6 off. |
| Restore IPv6 | `make restore-ipv6` | Restores the previous IPv6 settings. | Use this after a temporary IPv6 change. |

## Repository Setup and Discovery

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Setup | `make setup` | Runs the repository setup step after generating `.dockerignore`. | Use this when you want the baseline project setup without installing the full dev stack. |
| Setup development | `make setup-development` | Creates the development setup marker. | Use this when you want to prepare a development-specific setup state. |
| Bootstrap | `make bootstrap` | Installs dependencies and prepares the project. | Use this on a fresh machine or a new checkout. |
| Setup clean | `make setup-clean` | Cleans ignored files and then runs setup. | Use this when you want a clean setup pass. |
| List roles | `make list` | Prints the repository role list. | Use this when you need the current role inventory. |
| Tree view | `make tree` | Prints the repository tree. | Use this when you want a compact structural overview. |
| Meta graph inputs | `make mig` | Builds the meta graph inputs from `list` and `tree`. | Use this when you are generating or refreshing meta graph data. |

## Runtime Stack

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Start stack | `make up` | Starts the local compose stack and builds the image if it is missing. | Use this to bring the development stack online. |
| Stop stack | `make down` | Stops the compose stack and removes volumes. | Use this when you want a clean shutdown and disposable local state. |
| Pause services | `make stop` | Stops running services without removing volumes. | Use this when you want a fast stop and plan to start the same state again. |
| Restart stack | `make restart` | Stops the stack and starts it again. | Use this after configuration changes or when the stack needs a full restart. |
| Inspect container | `make exec` | Opens an interactive shell in the running infinito container. | Use this when you need to inspect live state or run a quick command inside the container. |

## Validation

### Lint

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Install lint tooling | `make install-lint` | Installs lint-related tooling. | Use this when you only need the lint stack. |
| Lint | `make lint` | Runs the main lint checks for the repository. | Use this when you want a broad lint pass before pushing. |
| Lint test suite | `make test-lint` | Runs the lint test suite inside the development environment. | Use this when you want CI-like lint validation. |
| Lint action | `make lint-action` | Runs the GitHub Actions lint checks. | Use this when you changed workflow files or workflow logic. |
| Lint Ansible | `make lint-ansible` | Runs the Ansible lint checks. | Use this when you changed Ansible roles, inventories, or playbook-related files. |
| Lint Python | `make lint-python` | Runs the Python lint checks. | Use this when you changed Python code. |
| Lint shell | `make lint-shellcheck` | Runs shellcheck lint checks. | Use this when you changed shell scripts. |

### Test

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Install dependencies | `make install` | Installs the repository tooling needed for development and tests. | Use this before running validation on a fresh machine or environment. |
| Unit tests | `make test-unit` | Runs the unit test suite. | Use this when you changed Python logic or other isolated code paths. |
| Integration tests | `make test-integration` | Runs the integration test suite. | Use this when your change affects behavior across modules or runtime boundaries. |
| Combined validation | `make test` | Runs the main combined validation flow. | Use this whenever a change touches at least one file that is not `.md` or `.rst`, or before opening a Pull Request. |

### Act

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Act workflow suite | `make act-all` | Runs the full local Act workflow suite. | Use this when you want to verify workflow behavior locally. |
| Act app workflow | `make act-app` | Runs the app-focused Act checks. | Use this when you are changing app-scoped workflow logic. |
| Act workflow file | `make act-workflow` | Runs one selected workflow with Act. | Use this when you want to focus on a single workflow file. |

## Cleanup

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Remove ignored files | `make clean` | Removes ignored files from the working tree. | Use this when you want to clear generated files without sudo. |
| Remove ignored files with sudo | `make clean-sudo` | Removes ignored files from the working tree with elevated privileges. | Use this when file ownership prevents a normal clean. |
| System purge | `make purge-system` | Runs `scripts/system/purge/system.sh` to clear repository, Docker, journald, package, and language caches. | Use this when disk usage is tight or you want the broad low-hardware cleanup pass. |
| Full purge | `make purge-all` | Runs `scripts/system/purge/all.sh`, which chains `make container-purge-system`, `make build-cleanup`, and `make purge-system`. | Use this when you want the broadest local cleanup bundle. |
| Refresh inventory | `make container-refresh-inventory` | Recreates the local inventory without deploying apps. | Use this when your local inventory is broken or you want a clean reset. |
| Purge app entity | `make container-purge-entity` | Purges one or more app entities inside the running container. | Use this before rerunning a purged app deployment. |
| Purge container state | `make container-purge-system` | Removes inventory, web config, and lib state in the running container. | Use this when you want a destructive local container reset. |

## Local Deploy

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Fresh kept app | `make deploy-fresh-kept-app` | Creates a new inventory and deploys one app. | Use this for the single-app fresh path. |
| Fresh purged app | `make deploy-fresh-purged-app` | Creates a new inventory, purges the app state, and redeploys one app. | Use this when you want a fresh app after cleanup. |
| Reuse kept app | `make deploy-reuse-kept-app` | Reuses an existing inventory and redeploys one app quickly. | Use this for the fast reuse path. |
| Reuse purged app | `make deploy-reuse-purged-app` | Reuses an existing inventory, purges the app state first, and redeploys one app quickly. | Use this when you want a fast reset-and-redeploy path. |
| Fresh kept all | `make deploy-fresh-kept-all` | Builds the broader local deployment flow across apps. | Use this when you explicitly need broad coverage. |
| Reuse kept all | `make deploy-reuse-kept-all` | Reuses the existing inventory and redeploys the broad app set. | Use this for the faster broad reuse path. |

## Notes

- The commands use the current `INFINITO_DISTRO` setting from the environment where relevant.
- For app-level local deploy flows and end-to-end checks, see [Development](../development/README.md).
- For validation strategy and Playwright guidance, see [Testing and Validation](../development/testing.md).
