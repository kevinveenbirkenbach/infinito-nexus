# playwright.spec.js

This page is the SPOT for automatically generating and updating role-local `playwright.spec.js` files.
Use this page for scenario design, selector strategy, and live end-to-end review.
For runner integration and repository-wide scenario requirements, see [Playwright Tests](../../../contributing/code/tests/playwright.md).
For the matching rendered input contract, see [Role `playwright.env.j2`](playwright.env.j2.md).

## Goal

- You MUST verify real user-facing browser flows from the supported entry point through a successful logout.
- You MUST keep the spec aligned with the role's actual login, navigation, and post-login behavior.
- You MUST capture user-visible behavior introduced by role-local `style.css`, `javascript.js`, or authentication integrations.

## Implement

- You MUST start from `APP_BASE_URL`, and if the role exposes the dashboard entry path, enter the application from the dashboard.
- You MUST verify login and logout end to end.
- When the role covers both `biber` and `administrator`, you MUST keep separate scenarios for both personas.
- When `style.css` or `javascript.js` is implemented or refactored, you MUST add or update Playwright assertions for the affected visible behavior.
- You MUST prefer stable selectors, accessible roles, and visible UI states over brittle DOM assumptions.
- You MUST use explicit waits for meaningful page state changes instead of fixed sleeps wherever practical.

## Avoid

- Do NOT stop at URL assertions or static text checks when the real requirement is a user-visible flow.
- Do NOT skip the logout path or finish while the session is still authenticated.
- Do NOT bypass the dashboard when the role is meant to start there.
- Do NOT rely on fragile selectors or timing hacks when more stable hooks exist.

## Review

- You MUST run the spec against the live application, not only against the file contents.
- You MUST inspect the start page and the login page as part of the end-to-end path.
- You MUST check the browser console for errors when the flow depends on injected JavaScript.
- You MUST check that changed CSS or JavaScript behavior is covered by the role-local Playwright suite.
- You MUST check that the application returns to a clearly logged-out state at the end of the test.
