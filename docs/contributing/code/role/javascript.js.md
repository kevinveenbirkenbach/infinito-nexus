[Back to Role](README.md)

# `javascript.js`

This page is the SPOT for role-local JavaScript injection and browser-side integration behavior.
Use this page for injector wiring, activation, and repository-wide behavior rules.
For implementation scope, DOM strategy, and live review, see [Agent `javascript.js`](../../../agents/files/role/javascript.js.md).

## `javascript.js.j2`

- `sys-front-inj-javascript` loads `templates/javascript.js.j2` when it exists and otherwise falls back to `files/javascript.js`.
- The injector runs when `compose.services.javascript.enabled` is enabled.
- The loaded script is collapsed into a one-liner before injection and added to the CSP hash list so inline execution remains consistent with the generated policy.
- Use `javascript.js.j2` when the script depends on role variables or inventory values, and use `files/javascript.js` when the script is static.

## Inventory

- Keep `compose.services.javascript.enabled` enabled in the role configuration or override it in the inventory when JavaScript injection should run.
- Pass only the runtime values that the browser logic actually needs. Keep the rendered template surface small and explicit.

## Repository Rules

- Use role-local JavaScript only for browser-side integration gaps that cannot be solved cleanly through app configuration or CSS alone.
- When OIDC is enabled, disable or hide the normal login form in the UI if the target application does not already provide a dedicated configuration switch for that behavior.
- Disable UI fields that are authored by OIDC or LDAP so users do not edit values locally that are managed by the identity provider or directory.
- Do not write values back from those UI fields to OIDC or LDAP through injected JavaScript. Treat those fields as externally managed and read-only in the application UI.
