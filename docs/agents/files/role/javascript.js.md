[Back to Role Files](README.md)

# javascript.js

This page is the SPOT for automatically generating and updating role-local `javascript.js`, `javascript.js.j2`, and equivalent injected browser entry files.
Use this page for implementation scope, DOM strategy, and live review.
For injector wiring, activation, and repository-wide behavior rules, see [Contributing `javascript.js`](../../../contributing/code/role/javascript.js.md).

## Goal

- Use role-local JavaScript only for browser-side gaps that cannot be solved cleanly through app configuration, server configuration, or CSS alone.
- Keep injected scripts small, explicit, and tightly scoped to the role's real integration need.
- Write the result so it adapts the upstream UI without turning the injected script into a fork of the application's frontend.

## Implement

- Use `templates/javascript.js.j2` when runtime values from the inventory or role variables must be rendered into the browser code.
- Use `files/javascript.js` when the script is static and does not depend on templating.
- Wait for the DOM before touching elements, and guard missing elements so unrelated pages do not break.
- Keep event handlers, observers, and DOM mutations idempotent because injected scripts may run on dynamic pages or be triggered repeatedly.
- Prefer stable selectors and narrow hooks over text matching or timing-based hacks.

## Avoid

- Do not reimplement server-side logic, authentication protocols, or business rules in injected JavaScript.
- Do not rewrite large parts of the frontend when a focused event handler, DOM adjustment, or configuration change is enough.
- Do not rely on fragile selectors, broad text matching, or timing hacks when more stable hooks exist.
- Do not introduce noisy debug logging, uncaught errors, duplicate event handlers, or endless observers into injected scripts.
- Do not break native login, logout, navigation, or form flows unless the role explicitly requires that change and the new behavior is verified end to end.

## Review

- Check the result with live inspection in the running application, not only by reading the JavaScript file.
- Compare the implemented behavior against the rendered UI so missing hooks, duplicate handlers, broken selectors, and unexpected side effects become visible.
- At minimum, inspect and compare the start page and the login page because these pages usually expose the most important navigation, authentication, and first-load behavior.
- Check the browser console for JavaScript errors or repeated side effects after the script is injected.
- If the change affects user-visible behavior, add or update the matching end-to-end coverage in [Role `playwright.spec.js`](playwright.spec.js.md).
- Check that the final JavaScript still feels like a small role-local adaptation of the target application, not a forked frontend implementation.
