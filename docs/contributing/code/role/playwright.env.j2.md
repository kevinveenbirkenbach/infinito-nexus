[Back to Role](README.md)

# `playwright.env.j2`

This page is the SPOT for role-local Playwright environment templates.
Use this page for runner discovery, `.env` rendering, and the repository-side variable contract.
For implementation scope, variable naming, and rendered-output review, see [Agent `playwright.env.j2`](../../../agents/files/role/playwright.env.j2.md).
For the matching scenario requirements, see [Contributing `playwright.spec.js`](playwright.spec.js.md).

## Role Contract

- `test-e2e-playwright` discovers Playwright-enabled roles through `templates/playwright.env.j2`.
- The file is rendered into `.env` and passed to the Playwright container through `--env-file`.
- The rendered environment must provide the inputs expected by the matching `files/playwright.spec.js`.

## Variable Rules

- `APP_BASE_URL` defines the supported start page of the role's test flow.
- If `compose.services.dashboard.enabled` is enabled, `APP_BASE_URL` should resolve to the dashboard URL because the test flow must start there.
- Provide additional app-specific URLs, feature flags, issuer URLs, and credentials only when the spec consumes them.
- Use explicit variable names that match the scenarios in the spec, especially when multiple personas such as `biber` and `administrator` are covered.
- Quote values with `dotenv_quote` when the rendered value may contain spaces or special characters.

## Scope

- Keep the template surface small and explicit.
- Do not use `playwright.env.j2` as a general dump for unrelated runtime variables.
- Put the scenario requirements in [Contributing `playwright.spec.js`](playwright.spec.js.md).
