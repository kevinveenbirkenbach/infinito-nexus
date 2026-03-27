[Back to CONTRIBUTING hub](../../CONTRIBUTING.md)

# Testing and Validation

Use the real commands from the repository. Run them from the repository root.

This repository uses several test and validation types:

- `Lint and syntax checks` catch style, formatting, and Ansible syntax problems early.
- `Unit tests` verify isolated logic.
- `Integration tests` verify behavior across modules and runtime boundaries.
- `Combined validation` runs the standard main verification flow.
- `Local deploy and E2E validation` checks whether apps and deployment flows work in a realistic local stack.

## Code Quality and Automated Checks

Use the following table to choose the right lint, syntax, unit, integration, or combined validation command for your change.

### Validation Commands

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Lint | `make lint` | Runs the main lint checks for the repository. | Use this when you want a broad lint pass before pushing. |
| Syntax | `make lint-ansible` | Runs the Ansible syntax validation for `playbook.yml`. | Use this when you changed Ansible roles, inventories, or playbook-related files. |
| Lint tests | `make test-lint` | Runs the lint test suite inside the development environment. | Use this when you want CI-like lint validation. |
| Unit tests | `make test-unit` | Runs the unit test suite. | Use this when you changed Python logic or other isolated code paths. |
| Integration tests | `make test-integration` | Runs the integration test suite. | Use this when your change affects behavior across modules or runtime boundaries. |
| Combined validation | `make test` | Runs the main combined validation flow. | Use this before opening a Pull Request or when you want the standard all-in-one check. |

## Local Deploy and End-to-End Checks

Use the following table when you need realistic local deployment validation or app-level end-to-end checks.

### Local Validation Commands

| Category | Command | What it does | When to use it |
|---|---|---|---|
| Local deploy | `APP=web-app-nextcloud make test-local-app` | Creates the needed inventory and deploys one app. | Use this for the first local validation of a single app. |
| Local deploy | `APP=web-app-nextcloud make test-local-rapid` | Reuses an existing local inventory and redeploys one app quickly. | Use this when you already have a working local setup and want faster iteration. |
| Local deploy and E2E | `APP=web-app-matomo make test-local-dedicated` | Runs a dedicated local validation flow for one app against the dev stack. | Use this when you want a stronger app-specific validation path. |
| Full local validation | `make test-local-full` | Builds the broader local deployment flow across apps. | Use this for a wider full-stack validation pass. |
| Local reset | `make test-local-reset` | Recreates the local inventory without deploying apps. | Use this when your local inventory is broken or you want a clean reset. |
| Local cleanup | `make test-local-cleanup` | Deletes local deploy state and cleanup data. | Use this only when you really want to remove local state. |

Important:

- Some local deploy commands are destructive.
- Read [scripts/tests/deploy/local/README.md](../../scripts/tests/deploy/local/README.md) before using reset or cleanup commands.
- After a successful local deploy, run `make trust-ca` and restart your browser.

## Playwright

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

## Testing Standards

### Common

Treat these rules as the baseline for all validation categories below.

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

### Development Procedure

- Analyze the code first.
- Build hypotheses before writing the test.
- Write the Playwright test.
- Run it against a fresh pure Docker image.
- Add additional procedures when relevant, for example OIDC or Keycloak.
- Start from the dashboard.
- End with a successful logout.

### Minimum Requirements

- The test must verify that login is possible.
- The test must verify that logout is possible.

