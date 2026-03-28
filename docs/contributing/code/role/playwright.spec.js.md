[Back to Role](README.md)

# `playwright.spec.js`

This page is the SPOT for role-local Playwright test specs.
Use this page for runner integration, minimum coverage, and repository-wide scenario requirements.
For implementation scope, selector strategy, and live review, see [Agent `playwright.spec.js`](../../../agents/files/role/playwright.spec.js.md).
For the matching rendered environment contract, see [Contributing `playwright.env.j2`](playwright.env.j2.md).

## Runner Contract

- `test-e2e-playwright` copies `files/playwright.spec.js` into the staged test project as `tests/playwright.spec.js`.
- The spec consumes the `.env` rendered from `templates/playwright.env.j2`.
- `package.json` and `playwright.config.js` MUST stay centralized in `roles/test-e2e-playwright/files/`.

## Requirements

- Every Playwright-enabled role MUST verify login and logout.
- Every role with `compose.services.dashboard.enabled` MUST start the test flow from the dashboard.
- When the role provides both `biber` and `administrator` scenarios, login and logout for both MUST be covered.
- When role-local `javascript.js` or `style.css` is implemented or refactored, the affected user-visible behavior MUST be added to or updated in the Playwright suite.
- Assertions MUST verify real UI states and user-visible outcomes, not only URL transitions or static strings.
- The suite MUST finish in a clearly logged-out state.

## Scenario Rules

- You MUST name tests after the real flow they verify, for example dashboard to app login and logout.
- You MUST keep persona-specific scenarios explicit when the role distinguishes between different user paths.
- You SHOULD add extra coverage when relevant, for example OIDC, LDAP, or dashboard-specific navigation.
