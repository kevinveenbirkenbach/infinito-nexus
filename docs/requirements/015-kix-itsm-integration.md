# 015 - KIX Service Management integration

## User Story

As an operator running an Infinito.Nexus stack, I want [KIX Start](https://www.kixdesk.com/) deployed as a first-class `web-app-*` role, fronted by `web-app-oauth2-proxy` so that **every** access to KIX is gated by Keycloak SSO with the realm's 2FA policy enforced — and so that helpdesk tickets share the same identity store, mail relay, dashboard, logout flow and proxy edge as every other service on the host.

## Acceptance Criteria

- [x] A new `roles/web-app-kix/` exists and conforms to the role-meta layout from [req-008](./008-role-meta-layout.md), [req-009](./009-per-role-networks-and-ports.md), [req-010](./010-role-meta-runafter-lifecycle-migration.md) and [req-011](./011-role-meta-info-migration.md): `meta/services.yml`, `meta/server.yml`, `meta/main.yml`, `meta/info.yml`, `vars/main.yml`, `tasks/main.yml` (thin wrapper with `run_once_web_app_kix` guard), `tasks/01_core.yml`, `templates/compose.yml.j2`, `README.md`.
- [x] The role declares its host-bound ports under `meta/services.yml.<entity>.ports.local.http` inside the `local.http` band from `group_vars/all/08_networks.yml`, picked via `cli meta ports suggest`.
- [x] The role declares a per-role docker subnet under `meta/server.yml.networks.local.subnet`, picked via `cli meta networks suggest`.
- [x] KIX is reachable at `kix.{{ DOMAIN_PRIMARY }}` over TLS through `sys-stk-front-proxy` and emits HSTS.
- [x] An `web-app-oauth2-proxy` instance sits between `sys-stk-front-proxy` and the KIX backend: every request to `kix.{{ DOMAIN_PRIMARY }}` that does not carry a valid OAuth2-proxy session cookie is redirected to Keycloak. The KIX backend is NOT reachable directly from the front proxy without traversing the OAuth2 proxy.
- [x] 2FA enforcement is realm-level: the Keycloak realm that backs the OAuth2 proxy has an OTP / WebAuthn flow configured, so a user without a second factor cannot complete the OAuth2 proxy redirect chain. The realm-level configuration is the single source of truth — no 2FA logic lives in KIX or the role itself.
- [x] LDAP is wired as KIX's user-directory backend against `svc-db-openldap` (`Auth::LDAP` + `Auth::Sync::LDAP`): when a user authenticates against KIX their profile (display name, email, role group) is sourced from LDAP — no manual KIX-side user pre-creation is required.
- [x] The `web-app-dashboard` role surfaces a card for KIX that links to its canonical URL, with the logo / title resolved via the standard `lookup('config', 'web-app-kix', ...)` path used by every other dashboard tile.
- [x] The universal logout endpoint terminates a KIX session like any other Infinito.Nexus app: the KIX session cookie is cleared and the browser lands on the project logout page.
- [x] An end-to-end Playwright spec at `roles/web-app-kix/files/playwright.spec.js` covers the in-scope flow: TLS root + HSTS at `kix.{{ DOMAIN_PRIMARY }}`; anonymous request to the canonical URL redirects into the OAuth2-proxy / Keycloak chain (the realm-level 2FA step is exercised by the shared `web-app-keycloak` Playwright suite, not duplicated per-app).

## Deferred (KIX 18 OSS frontend limitation)

KIX 18 OSS exposes both `Auth::HTTPBasicAuth` (which reads
`REMOTE_USER` / `HTTP_REMOTE_USER` — semantically equivalent to
OTRS' `Auth::HTTPHeaderModule`) and a fully featured
`Auth::LDAP` + `Auth::Sync::LDAP` backend, so both are wired by
this role. The KIX 18 Angular frontend SPA, however, ships its own
login route (`/auth?redirectUrl=…`) and does not auto-submit
credentials based on the API-side `Remote-User` env. As a result
an authenticated oauth2-proxy session reaches the KIX UI and the
backend trusts the forwarded identity for API requests, but the
SPA still renders its own login form on first visit; the user
re-authenticates against the KIX login form against `Auth::LDAP`.

A truly transparent SPA-side SSO (login form skipped) requires a
small KIX frontend modification — wired to the existing
`Auth::HTTPBasicAuth` endpoint — and is tracked as a follow-on
iteration, not part of req-015.
