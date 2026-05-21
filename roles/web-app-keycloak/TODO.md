# Todos

- Implement working logout for all applications
- Implement general logout button

## Req 019 rollout: deploy gate

- During the autonomous req 019 rollout, `make deploy-fresh-purged-apps INFINITO_APPS=web-app-keycloak INFINITO_FULL_CYCLE=true` failed with two unrelated assertions:
  - `kcadm.sh config credentials` failed during the keycloak admin login phase (likely transient or env-scoped).
  - `run_once_web_app_mailu is defined` assertion failed in `sys-svc-mail`, indicating the service-loader did not preload Mailu in the keycloak-only deploy path.
- These are deployment-orchestration failures, not playwright-parity failures, and were therefore deferred per the [autonomy escape clause](../../docs/requirements/019-playwright-meta-services-parity.md#autonomy).
- The role's playwright lint contracts (Tests A + B + env_keys_used) are green; role-closure remains pending the orchestration fix.
