# Todos

## Req 019 rollout — deploy gate

- The persona scenarios (`biber: dashboard → app → universal logout`, `administrator: dashboard → prometheus → app → universal logout`) fail after a real successful Keycloak login: the dashboard's `oidc.js` keeps `authenticated=false` after the post-login redirect, so the Account/Logout menu never surfaces and the persona helper has nothing to click. The dashboard's own `keycloak-js` init / silent-SSO chain needs fixing — once `keycloak.authenticated` correctly flips to true after a code-flow round-trip the persona helpers (now waiting via `Locator.waitFor` and only accepting iframe URL fallbacks) will close the loop without further changes.
- Deferred per the [autonomy escape clause](../../docs/requirements/019-playwright-meta-services-parity.md#autonomy).
