# OpenTalk (web-app-opentalk)

Sovereign open-source video conferencing — Heinlein-Group OpenTalk stack with the upstream **controller** + **web-frontend** + **LiveKit** media server, integrated with the project's central Keycloak (OIDC) and OpenLDAP via the controller's `keycloak_webapi` user-search backend.

## Architecture

| Container | Image | Role |
|---|---|---|
| `application` | `registry.opencode.de/opentalk/controller` | REST API + signaling |
| `frontend` | `registry.opencode.de/opentalk/web-frontend` | React UI served on `talk.{{ DOMAIN_PRIMARY }}` |
| `livekit` | `livekit/livekit-server` | WebRTC SFU (network_mode: host for media UDP) |
| Postgres | `svc-db-postgres` (shared) | controller persistence |
| Redis | dedicated | controller pub/sub |
| TURN | `web-svc-coturn` (shared, req 001) | STUN/TURN relay |

## Hostname

- Canonical: `talk.{{ DOMAIN_PRIMARY }}`

## IAM

- OIDC issuer: shared Keycloak realm
- Controller uses Keycloak admin Web API for user search (`api_base_url = .../admin/realms/<realm>`)
- LDAP not directly accessed; OpenLDAP feeds Keycloak, Keycloak feeds OpenTalk

See [docs/IAM.md](docs/IAM.md) and [docs/LDAP.md](docs/LDAP.md).

## Cross-integration

- OpenCloud is exposed to the frontend as the file-picker backend via `SHARED_FOLDER_OPENCLOUD_URL`.

## Out of scope (v1)

- MinIO assets / recordings — controller config tolerates absence; recording features disabled.
- RabbitMQ-driven mailer / recorder workers — not deployed; in-app email triggers fall through.

## Documentation

- Upstream docs: <https://docs.opentalk.eu/>
- Setup repo: <https://gitlab.opencode.de/opentalk/ot-setup>
