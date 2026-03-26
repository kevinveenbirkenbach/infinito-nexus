# Contributing to Infinito.Nexus

This guide is for both human contributors and AI assistants.
It explains the expected setup, contribution workflow, testing, review, and AI usage for this repository.

The [Development Hub](https://s.infinito.nexus/development) is the central information hub for developers and contains further guidance, discussion, and exchange with other contributors.
New permanent team members should follow the [onboarding document](https://s.infinito.nexus/onboarding).

## Quick Start

If you only read one section, read this one:

1. Create a fork and a feature branch.
2. Set up your local environment.
3. Make a focused change.
4. Run the relevant checks.
5. Push to your fork.
6. Open a Pull Request with the right template.
7. Request review and address feedback in your fork.

## Development Environment Setup

Use the repository's real setup flow. The main source of truth is the [Makefile](Makefile).

Important:

- Some local development commands change host settings such as [DNS](https://en.wikipedia.org/wiki/Domain_Name_System), [AppArmor](https://en.wikipedia.org/wiki/AppArmor), and [IPv6](https://en.wikipedia.org/wiki/IPv6).
- Some commands use `sudo`.
- Read the setup guides first if you are new to this environment.
- The local development workflow is mainly tested on Linux.

### Platform-Specific Instructions

#### Linux

On Linux, follow the normal local setup guide and use the repository commands directly on your machine. More information [here](https://s.infinito.nexus/localenv).

#### macOS

On macOS, use [Lima](https://lima-vm.io/) so the project runs inside a Linux environment instead of directly on the host system.
Use [Homebrew](https://brew.sh/) on macOS to install and manage Lima, then run the normal Linux-oriented project setup inside the Lima environment.
This keeps the development workflow closer to the Linux-first setup used by this repository.
More information [here](https://s.infinito.nexus/localenv).

#### Windows (WSL2)

On Windows, use [WSL2](https://learn.microsoft.com/en-us/windows/wsl/about) as the development environment and run the repository commands inside WSL2, not directly in [PowerShell](https://learn.microsoft.com/en-us/powershell/).
Use Ubuntu 24.04 with [Docker Desktop WSL2 integration](https://docs.docker.com/desktop/features/wsl/), enable [`systemd`](https://systemd.io/), and expect a few Windows-specific follow-up steps around [certificate authority (CA)](https://en.wikipedia.org/wiki/Certificate_authority) trust and local name resolution.

Keep these WSL2 specifics in mind:

- Trust the generated [CA](https://en.wikipedia.org/wiki/Certificate_authority) in Windows, not only inside WSL2.
- If `*.infinito.example` does not resolve correctly, check Windows-side [DNS](https://en.wikipedia.org/wiki/Domain_Name_System) or hosts configuration.
- If container or security setup behaves differently than on Linux, the WSL2 guide covers the usual [Docker Buildx](https://docs.docker.com/reference/cli/docker/buildx/), [DNS](https://en.wikipedia.org/wiki/Domain_Name_System), and [AppArmor](https://en.wikipedia.org/wiki/AppArmor)-related workarounds.

More information and detailed instructions [here](https://s.infinito.nexus/wsl2env).

### Platform Agnostic

These steps are the shared repository workflow and apply regardless of whether you work on Linux, macOS, or Windows with WSL2.

#### Bootstrap

Run these commands from the repository root:

```bash
make bootstrap
make dev-environment-bootstrap
make up
make trust-ca
```

##### Bootstrap Commands

| Phase | Command | What it does |
|---|---|---|
| Initial setup | `make bootstrap` | Installs project dependencies and runs the first repository setup. |
| Host preparation | `make dev-environment-bootstrap` | Prepares the local development machine for the project workflow. |
| Start stack | `make up` | Starts the local development stack. |
| Browser trust | `make trust-ca` | Trusts the generated local [CA](https://en.wikipedia.org/wiki/Certificate_authority) so `*.infinito.example` works correctly in your browser. |

#### Teardown

When you are done, use these commands to stop the stack and clean up the local environment:

```bash
make down
make dev-environment-teardown
```

##### Teardown Commands

| Phase | Command | What it does |
|---|---|---|
| Stop stack | `make down` | Stops the local development stack. |
| Host cleanup | `make dev-environment-teardown` | Reverts local development environment changes where supported. |

### Full Development Flow

The repository already contains a development helper script at [development.sh](scripts/tests/development.sh). The commands from that file are explained here as the intended end-to-end flow.

##### Flow Summary

| Step | Command | Purpose in this flow |
|---|---|---|
| 1 | `make install` | Installs the dependencies needed before running the local development flow. |
| 2 | `make dev-environment-bootstrap` | Prepares the host machine for local development. |
| 3 | `make up` | Starts the development stack. |
| 4 | `make test` | Runs the main combined validation flow. |
| 5 | `APP=web-app-matomo make test-local-dedicated` | Runs a stronger local validation path for one concrete app. |
| 6 | `make trust-ca` | Makes the generated local certificates trusted by the host browser. |
| 7 | `make down` | Stops the running development stack. |
| 8 | `make dev-environment-teardown` | Cleans up host-side development environment changes. |

Use this as a practical reference when you want to understand how local development is expected to work.

### Local Deployment Shortcuts

The local deploy targets are summarized in the tables in the `Testing and Validation` section below.

Important:

- Some local deploy commands are destructive.
- Read [README.md](scripts/tests/deploy/local/README.md) before using reset or cleanup commands.
- After a successful local deploy, run `make trust-ca` and restart your browser.
More information [here](https://s.infinito.nexus/localenv).

## Contribution Flow

This repository uses a strict fork-first workflow.

- Do not commit directly to `main`.
- Do all work in your own fork.
- Open Pull Requests from your fork back to the main repository.

Why this matters:

- `main` should stay stable.
- Shared CI resources are limited.
- Broken experimental work should not run in the main repository.

### Step-by-Step Flow

1. Create or update your fork.
2. Create a feature branch in your fork.
3. Make one focused change at a time.
4. Run the relevant local checks.
5. Push the branch to your fork.
6. Wait until the CI in your fork is green.
7. Open a Pull Request.
8. Address review feedback in your fork.

More information about the contribution workflow is available [here](https://s.infinito.nexus/forking).

### Choose the Right Pull Request Template

Pick the template that matches your change:
All Pull Request templates are located in [PULL_REQUEST_TEMPLATE](.github/PULL_REQUEST_TEMPLATE).

| Change type | Template |
|---|---|
| Server and `web-*` changes | [server.md](.github/PULL_REQUEST_TEMPLATE/server.md) |
| Workstation and `desk-*` changes | [workstation.md](.github/PULL_REQUEST_TEMPLATE/workstation.md) |
| Shared system changes such as `sys-*`, `svc-*`, `dev-*`, `drv-*`, `pkgmgr`, `update-*`, or `user-*` | [system.md](.github/PULL_REQUEST_TEMPLATE/system.md) |
| CI/CD and workflow changes | [pipeline.md](.github/PULL_REQUEST_TEMPLATE/pipeline.md) |
| Documentation-only changes | [documentation.md](.github/PULL_REQUEST_TEMPLATE/documentation.md) |
| Agent-specific changes | [agents.md](.github/PULL_REQUEST_TEMPLATE/agents.md) |

### Pull Request Checklist

Before you open a Pull Request, make sure:

- CI in your fork is green.
- Your branch is up to date with `main`.
- Your change is small and focused.
- Your Pull Request explains the problem, the solution, and the test result.
- Relevant documentation is updated.
- The correct Pull Request template is used.
- The Pull Request is linked to the related work item in [project.infinito.nexus](https://project.infinito.nexus/) and back.
- Screenshots, logs, traces, or migration notes are attached when they help review the change.

### CI Failures and Debugging

If CI fails, follow a clean debugging workflow:

1. Export the raw failing logs.
2. Save them locally as `job-logs.txt`.
3. Decide whether the failure belongs to your branch or to something unrelated.
4. Fix related failures in the same branch.
5. Open an issue for unrelated failures instead of mixing them into your branch.

Important:

- Do not debug from screenshots alone. Use raw logs.
- Do not commit log files to the repository.
- If a [Playwright](https://playwright.dev/) job fails, also download the Playwright assets, store them in `/tmp/`, and analyze them together with the logs.
More information [here](https://hub.infinito.nexus/t/infinito-nexus-ci-cd-debugging-guide/462).

### Use Targeted Manual CI Jobs

Do not rerun the full CI over and over if you only need one focused check.

Prefer the manual workflow in [entry-manual.yml](.github/workflows/entry-manual.yml):

- Select your branch.
- Use `debian` unless you have a clear reason to use a different distro.
- Limit the run to the affected app when possible.

This gives faster feedback and protects shared CI runners.

## Testing and Validation

Use the real commands from the repository. Run them from the repository root.

This repository uses several test and validation types:

- `Lint and syntax checks` catch style, formatting, and Ansible syntax problems early.
- `Unit tests` verify isolated logic.
- `Integration tests` verify behavior across modules and runtime boundaries.
- `Combined validation` runs the standard main verification flow.
- `Local deploy and E2E validation` checks whether apps and deployment flows work in a realistic local stack.

### Code Quality and Automated Checks

Use the following table to choose the right lint, syntax, unit, integration, or combined validation command for your change.

#### Validation Commands

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Lint | `make lint` | Runs the main lint checks for the repository. | Use this when you want a broad lint pass before pushing. |
| Syntax | `make lint-ansible` | Runs the Ansible syntax validation for `playbook.yml`. | Use this when you changed Ansible roles, inventories, or playbook-related files. |
| Lint tests | `make test-lint` | Runs the lint test suite inside the development environment. | Use this when you want CI-like lint validation. |
| Unit tests | `make test-unit` | Runs the unit test suite. | Use this when you changed Python logic or other isolated code paths. |
| Integration tests | `make test-integration` | Runs the integration test suite. | Use this when your change affects behavior across modules or runtime boundaries. |
| Combined validation | `make test` | Runs the main combined validation flow. | Use this before opening a Pull Request or when you want the standard all-in-one check. |

### Local Deploy and End-to-End Checks

Use the following table when you need realistic local deployment validation or app-level end-to-end checks.

#### Local Validation Commands

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Local deploy | `APP=web-app-nextcloud make test-local-app` | Creates the needed inventory and deploys one app. | Use this for the first local validation of a single app. |
| Local deploy | `APP=web-app-nextcloud make test-local-rapid` | Reuses an existing local inventory and redeploys one app quickly. | Use this when you already have a working local setup and want faster iteration. |
| Local deploy and E2E | `APP=web-app-matomo make test-local-dedicated` | Runs a dedicated local validation flow for one app against the dev stack. | Use this when you want a stronger app-specific validation path. |
| Full local validation | `make test-local-full` | Builds the broader local deployment flow across apps. | Use this for a wider full-stack validation pass. |
| Local reset | `make test-local-reset` | Recreates the local inventory without deploying apps. | Use this when your local inventory is broken or you want a clean reset. |
| Local cleanup | `make test-local-cleanup` | Deletes local deploy state and cleanup data. | Use this only when you really want to remove local state. |

### Playwright

[Playwright](https://playwright.dev/) tests are part of deployment and end-to-end validation for `web-*` roles. They are not exposed here as a separate top-level `make` command.

To enable Playwright for a `web-*` role, provide:

- `templates/playwright.env.j2`
- `files/playwright.spec.js`

During the deploy stage, the shared `test-e2e-playwright` role:

- discovers the relevant app roles
- stages the test project
- renders the `.env`
- injects the shared `package.json` and `playwright.config.js`
- waits until the app is reachable
- runs Playwright in Docker

In practice, Playwright coverage is usually exercised through local deploy flows and deploy CI runs. Every `web-*` suite should verify at least login and logout.

## Review Requirements

Open a Pull Request only when it is ready for real review.

The matching Pull Request template is the SPOT for PR structure, required author input, and review context. Use the correct template from [PULL_REQUEST_TEMPLATE](.github/PULL_REQUEST_TEMPLATE) and orient your Pull Request to it.
The [Coding Standards](#coding-standards) section is the SPOT for repository-wide code quality expectations such as diff quality, maintainability, and conventions.

In addition to the templates, keep these repository-wide review rules in mind:

- Keep commit history clear and reviewable.
- Code ownership is defined in [CODEOWNERS](.github/CODEOWNERS).
- Auth, proxy, TLS, networking, migrations, and shared abstractions deserve extra review attention.
- Attach screenshots, traces, logs, and migration notes when they materially help validate the change.

More information [here](https://s.infinito.nexus/reviewguide).

## AI Best Practices

AI assistants are welcome, but they must follow the same workflow as humans.

This file is the SPOT for contributor workflow, testing, review, and coding standards.
[AGENTS.md](AGENTS.md) is the SPOT for agent-specific execution rules and repository-wide agent behavior.

Additional AI-specific rules:

- Read [AGENTS.md](AGENTS.md) before making changes.
- Do not invent commands, workflows, or files that do not exist.
- Keep explanations simple and explicit.
- State assumptions clearly.
- Never expose secrets in prompts, code, screenshots, or logs.
- Treat AI output as a draft that must be reviewed for wrong assumptions, duplicate logic, and security mistakes.
- Keep agent instructions consistent: [AGENTS.md](AGENTS.md) is the repository-wide source of truth, while [CLAUDE.md](CLAUDE.md) and [GEMINI.md](GEMINI.md) are tool-specific additions.

More information here:

- [AI best practices](https://s.infinito.nexus/aibestpractice)
- [Review guide](https://s.infinito.nexus/reviewguide)

## Coding Standards

This repository values simple, maintainable, and well-tested changes.

### Principles

Follow these principles:

- [DRY](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself)
- [SPOT](https://en.wikipedia.org/wiki/Single_source_of_truth)
- [KISS](https://en.wikipedia.org/wiki/KISS_principle)
- [Agile Manifesto](https://agilemanifesto.org/)
- [Zen of Python](https://en.wikipedia.org/wiki/Zen_of_Python) for all code
- [TDD](https://en.wikipedia.org/wiki/Test-driven_development)

### Diff Quality

- Keep diffs focused, readable, and easy to review.
- Avoid duplicate, conflicting, or purely cosmetic churn unless formatting cleanup is part of the task.
- Prefer semantic improvements that reduce maintenance effort.

### Lint

Use these linting and quality tools where applicable:

- [ruff](https://github.com/astral-sh/ruff)
- [shellcheck](https://github.com/koalaman/shellcheck)
- [hadolint](https://github.com/hadolint/hadolint)

### Refactoring

- If you touch a file, refactor it according to these coding standards where practical.
- If similar logic exists elsewhere in the project, refactor it toward a shared implementation.

### Testing Standards

- Write tests in the `tests` folder.
- Use Python `unittest` for unit, integration, and lint tests.
- Do not write tests that only check whether a file contains a string.
- Do not write tests only for non-executable files such as `.yml` or `.j2`.
- Test the behavior that consumes the configuration.

### Unit

- For touched `*.py` files, add or update unit tests in `tests/unit`.
- For touched `*.py` files, add or update integration tests in `tests/integration`.

### Playwright

- Playwright tests are required for `web-*` roles.
- Every Playwright test suite must verify login and logout.

#### Development Procedure

- Analyze the code first.
- Build hypotheses before writing the test.
- Write the Playwright test.
- Run it against a fresh pure Docker image.
- Add additional procedures when relevant, for example OIDC or Keycloak.
- Start from the dashboard.
- End with a successful logout.

#### Minimum Requirements

- The test must verify that login is possible.
- The test must verify that logout is possible.

### Architecture

- Prefer `Dockerfile` over `Dockerfile.j2`.
- Prefer defining shared variables once in `vars/main.yml`.
- Treat constants as uppercase when they are defined once and used as fixed values.
- For `web-*` roles, test against the original upstream Docker image when practical.

### Documentation and Comments

- Keep core information inside the repository, either in code or in `.md` files.
- Use `.md` files for commands, workflows, setup, and contributor guidance.
- Do not use `.md` files to describe implementation logic that is already visible in the code.
- Write code so it is logical and self-explanatory and usually does not need comments.
- Add code comments only when an exception, edge case, or surprising decision would otherwise confuse readers.
- Use comments to explain why something is unusual, not to restate what obvious code already does.

### Semantics and Writing

- Keep code and comments in English.
- Fix nearby wording and semantic issues when you touch a file.

## Need Help

For general discussion:
More information [here](https://hub.infinito.nexus/).

For bug reports and actionable feature requests:
More information [here](https://s.infinito.nexus/issues).

## Code of Conduct

All contributors must follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Join the Project

If you want to join the project as a paid long-term contributor, write to [hr@infinito.nexus](mailto:hr@infinito.nexus) or request a meeting [here](https://s.infinito.nexus/meet).
