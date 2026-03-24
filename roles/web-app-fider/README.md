# web-app-fider

Deploys [Fider](https://getfider.com/) — an open-source community feedback and voting platform — as part of the Infinito.Nexus stack.

## Features

- Single-container deployment via Docker Compose
- PostgreSQL database (all data including attachments stored in the database — no extra volumes)
- Email verification mandatory before voting (via SMTP / Mailu)
- HTTPS enforced via NGINX reverse proxy
- Keycloak OIDC configured automatically via database on first deploy
- Accessible at `https://fider.<your-domain>`

## SSO / Authentication

Fider has native OAuth2 support. Unlike Mattermost, it has no env vars or CLI for OAuth2 — configuration is stored directly in the `oauth_providers` PostgreSQL table. The setup task inserts the Keycloak provider on first deploy (idempotent via `ON CONFLICT DO UPDATE`), using `status=2` (enabled) and `is_trusted=true`.

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `compose.services.oidc.enabled` | `true` | Automate Keycloak OIDC setup |
| `compose.services.database.type` | `postgres` | Database engine (postgres only) |
| `compose.services.fider.version` | `stable` | Docker image tag |
| `server.domains.canonical` | `fider.{{ DOMAIN_PRIMARY }}` | Public domain |

## References

- [Fider Hosting Guide](https://getfider.com/docs/hosting)
- [Fider GitHub](https://github.com/getfider/fider)
