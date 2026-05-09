# Todos

- Check if DKIM generation works on new setups
- Implement auto reverse DNS
- Activate IP6
- Fix `sys-svc-mail` ↔ `web-app-mailu` preload ordering. `make deploy-fresh-purged-apps APPS=web-app-mailu FULL_CYCLE=true` fails on `sys-svc-mail/tasks/01_core.yml` line 9 with `assertion: run_once_web_app_mailu is defined → false`. The constructor stage runs `sys-svc-mail` before `sys-utils-service-loader` has loaded mailu, so the assertion fires. Needs root-cause fix in the loader-vs-svc-mail include order; documented for req 019 autonomy escape clause (failure unrelated to the persona-spec rollout).
- Fix the preceding `kcadm.sh config credentials` failure inside the keycloak container that surfaces during the `web-app-mailu` deploy (Keycloak admin auth path); also pre-existing and unrelated to req 019.
