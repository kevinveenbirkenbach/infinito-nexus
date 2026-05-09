# Todos

## Req 019 rollout — deploy gate

- During the autonomous req 019 rollout, `make deploy-fresh-purged-apps APPS=web-app-dashboard FULL_CYCLE=true` failed because two pre-existing tests in `files/playwright.spec.js` timed out (`dashboard loads core css, javascript, simpleicons, and logo assets` at L617 and `dashboard login automatically switches Login to Account and exposes Logout under Account` at L723).
- These failures predate the req 019 rollout edits (the rollout only appended persona-contract and per-service-contract tests; the failing tests are the original dashboard integration scenarios).
- Likely environmental (asset-host wiring or Keycloak readiness in the deploy sandbox), not playwright-parity related.
- Deferred per the [autonomy escape clause](../../docs/requirements/019-playwright-meta-services-parity.md#autonomy).
- Lint contracts (Tests A + B + env_keys_used) are green for the role; role-closure pending the integration-test stabilisation.
