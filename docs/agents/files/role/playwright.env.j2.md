[Back to Role Files](README.md)

# playwright.env.j2

This page is the SPOT for automatically generating and updating role-local `playwright.env.j2` files.
Use this page for the rendered test input surface, variable naming, and entry-point selection.
For runner discovery, staging, and repository-side contract rules, see [Contributing `playwright.env.j2`](../../../contributing/code/role/playwright.env.j2.md).
For the matching scenario implementation, see [Role `playwright.spec.js`](playwright.spec.js.md).

## Goal

- Provide only the environment values that the role-local Playwright suite actually needs.
- Keep variable names stable between `playwright.env.j2` and `playwright.spec.js`.
- Render the real entry point, URLs, feature flags, and credentials that the deployed role exposes.

## Implement

- Define `APP_BASE_URL` as the real start page of the test flow.
- If `compose.services.dashboard.enabled` is enabled for the role, point `APP_BASE_URL` to the dashboard entry instead of jumping directly into the app.
- Expose app-specific base URLs, issuer URLs, feature flags, and credentials only when the spec consumes them.
- Use `dotenv_quote` for values that may contain spaces, special characters, or shell-sensitive content.
- When the suite covers multiple personas such as `biber` and `administrator`, expose separate variables for each scenario instead of overloading one shared credential pair.

## Avoid

- Do not expose unused variables, duplicate values, or secrets that the spec never reads.
- Do not hardcode domains or credentials that should come from role variables, inventory, or lookups.
- Do not let variable names drift away from the names consumed in `playwright.spec.js`.
- Do not point tests directly to the app when the supported user journey starts in the dashboard.

## Review

- Check that every environment variable referenced in `playwright.spec.js` is present in the rendered `.env`.
- Check that `APP_BASE_URL`, app URLs, issuer URLs, and feature toggles match the deployed role.
- Check that persona-specific credentials such as `biber` and `administrator` map to the intended scenarios.
