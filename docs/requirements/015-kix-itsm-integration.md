# 015 - KIX Service Management integration

## User Story

As an operator running an Infinito.Nexus stack, I want [KIX Start](https://www.kixdesk.com/) deployed as a first-class `web-app-*` role, fronted by `web-app-oauth2-proxy` so that **every** access to KIX is gated by Keycloak SSO with the realm's 2FA policy enforced — and so that helpdesk tickets share the same identity store, mail relay, dashboard, logout flow and proxy edge as every other service on the host.

## Acceptance Criteria

- [ ] A new `roles/web-app-kix/` exists and conforms to the role-meta layout from [req-008](./008-role-meta-layout.md), [req-009](./009-per-role-networks-and-ports.md), [req-010](./010-role-meta-runafter-lifecycle-migration.md) and [req-011](./011-role-meta-info-migration.md): `meta/services.yml`, `meta/server.yml`, `meta/main.yml`, `meta/info.yml`, `vars/main.yml`, `tasks/main.yml` (thin wrapper with `run_once_web_app_kix` guard), `tasks/01_core.yml`, `templates/compose.yml.j2`, `README.md`.
- [ ] The role declares its host-bound ports under `meta/services.yml.<entity>.ports.local.http` inside the `local.http` band from `group_vars/all/08_networks.yml`, picked via `cli meta ports suggest`.
- [ ] The role declares a per-role docker subnet under `meta/server.yml.networks.local.subnet`, picked via `cli meta networks suggest`.
- [ ] KIX is reachable at `kix.{{ DOMAIN_PRIMARY }}` over TLS through `sys-stk-front-proxy` and emits HSTS.
- [ ] An `web-app-oauth2-proxy` instance sits between `sys-stk-front-proxy` and the KIX backend: every request to `kix.{{ DOMAIN_PRIMARY }}` that does not carry a valid OAuth2-proxy session cookie is redirected to Keycloak. The KIX backend is NOT reachable directly from the front proxy without traversing the OAuth2 proxy.
- [ ] 2FA enforcement is realm-level: the Keycloak realm that backs the OAuth2 proxy has an OTP / WebAuthn flow configured, so a user without a second factor cannot complete the OAuth2 proxy redirect chain. The realm-level configuration is the single source of truth — no 2FA logic lives in KIX or the role itself.
- [ ] After a successful 2FA login the OAuth2 proxy forwards the authenticated identity to the KIX backend via an HTTP header (e.g. `X-Forwarded-User` / `REMOTE_USER`); KIX is configured to trust that header (`Auth::HTTPHeaderModule` for agents, `CustomerAuth::HTTPHeaderModule` for customers) and the user lands directly in the authenticated KIX UI without a second KIX-side login form.
- [ ] LDAP is wired as KIX's user-directory backend against `svc-db-openldap`: when an OAuth2-proxy-forwarded user reaches KIX for the first time, KIX resolves the user's profile (display name, email, group membership) from LDAP — no manual KIX-side user pre-creation is required.
- [ ] Outbound notification mail flows through `sys-svc-mail-smtp`: a KIX-triggered notification leaves the host via the project's SMTP relay (verified by checking the relay's mail log for the KIX submission).
- [ ] The `web-app-dashboard` role surfaces a card for KIX that links to its canonical URL, with the logo / title resolved via the standard `lookup('config', 'web-app-kix', ...)` path used by every other dashboard tile.
- [ ] The universal logout endpoint terminates a KIX session like any other Infinito.Nexus app: the KIX session cookie is cleared and the browser lands on the project logout page.
- [ ] `roles/web-app-kix/README.md` lists the supported integrations explicitly (OAuth2-proxy + Keycloak 2FA, LDAP user directory, SMTP, dashboard, logout) AND the integrations that this requirement intentionally does NOT cover, so future requirements can pick them up individually:
  - Bi-directional ticket linking with OpenProject and GitLab
  - XWiki knowledge-base content embedding (URL references via KIX dynamic fields are operator-configurable but not part of this AC set)
  - Nextcloud as attachment storage backend
  - ActivityPub / federation
- [ ] An end-to-end Playwright spec at `roles/web-app-kix/files/playwright.spec.js` covers the in-scope flow: anonymous request to `kix.{{ DOMAIN_PRIMARY }}` redirects to the Keycloak login (OAuth2-proxy challenge); login as a known inventory user — including the realm's 2FA step — lands directly in the authenticated KIX UI without a second KIX-side login form; the universal logout endpoint signs the user out at both layers, and a follow-up unauthenticated request to the canonical URL is redirected back to Keycloak rather than reaching the authenticated KIX UI.
- [ ] This requirement file is cross-linked from the implementing PR; the PR description references this file.
