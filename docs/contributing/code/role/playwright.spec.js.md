[Back to Role](README.md)

# `playwright.spec.js`

This page is the SPOT for role-local Playwright test specs.
Use this page for runner integration, minimum coverage, and repository-wide scenario requirements.
For implementation scope, selector strategy, and live review, see [Agent `playwright.spec.js`](../../../agents/files/role/playwright.spec.js.md).
For the matching rendered environment contract, see [Contributing `playwright.env.j2`](playwright.env.j2.md).

## Runner Contract

- `test-e2e-playwright` copies `files/playwright.spec.js` into the staged test project as `tests/playwright.spec.js`.
- The spec consumes the `.env` rendered from `templates/playwright.env.j2`.
- `package.json` and `playwright.config.js` stay centralized in `roles/test-e2e-playwright/files/`.

## Requirements

- Every Playwright-enabled role must verify login and logout.
- Every role with `compose.services.dashboard.enabled` must start the test flow from the dashboard.
- When the role provides both `biber` and `administrator` scenarios, login and logout for both must be covered.
- When role-local `javascript.js` or `style.css` is implemented or refactored, the affected user-visible behavior must be added to or updated in the Playwright suite.
- Assertions must verify real UI states and user-visible outcomes, not only URL transitions or static strings.
- The suite must finish in a clearly logged-out state.

## Scenario Rules

- Name tests after the real flow they verify, for example dashboard to app login and logout.
- Keep persona-specific scenarios explicit when the role distinguishes between different user paths.
- Add extra coverage when relevant, for example OIDC, LDAP, or dashboard-specific navigation.
