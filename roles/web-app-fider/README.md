# Fider

Deploys [Fider](https://getfider.com/) — an open-source community feedback and voting platform — as part of the Infinito.Nexus stack.

## Features

- Single-container deployment via Docker Compose
- PostgreSQL database (all data including attachments stored in the database — no extra volumes needed)
- SSO via Keycloak configured automatically on first deploy
- Email notifications via Mailu (optional)
- HTTPS enforced via NGINX reverse proxy
- Accessible at `https://fider.<your-domain>`

## SSO / Authentication

Fider has native OAuth2 support but **no environment variables or CLI** for configuring it — the provider is stored directly in the `oauth_providers` PostgreSQL table.

The setup tasks (`tasks/01_setup_oidc.yml`) handle the full first-deploy bootstrap automatically:

1. **Tenant bootstrap** — calls Fider's `POST /_api/tenants` API to create the initial tenant. The API creates the tenant with `status=2` (pending email verification) and does not yet create any user record.
2. **Admin user creation** — the admin user is inserted directly into the `users` table (`role=3` = Administrator, `status=1` = Active), bypassing email verification. The `email_verifications` record is also marked as verified. Both operations are idempotent (`WHERE NOT EXISTS` / `WHERE verified_at IS NULL`).
3. **Tenant activation** — sets `status=1` on the tenant row so Fider serves the public page instead of showing a "pending activation" screen.
4. **OIDC provider** — inserts the Keycloak provider into `oauth_providers` with `status=2` (enabled) and `is_trusted=true`. Idempotent via `ON CONFLICT (tenant_id, provider) DO UPDATE`.

When a user logs in via Keycloak for the first time, Fider matches their email to the existing admin user and links the OIDC provider automatically.

To enable SSO, set `compose.services.oidc.enabled: true` (the default) in your inventory and ensure `OIDC.CLIENT.SECRET` is configured.

## Configuration

Key settings in `config/main.yml`:

| Key | Default | Description |
|-----|---------|-------------|
| `compose.services.oidc.enabled` | `true` | Automate Keycloak OIDC setup |
| `compose.services.database.type` | `postgres` | Database engine (postgres only) |
| `compose.services.fider.version` | `stable` | Docker image tag |
| `server.domains.canonical` | `fider.{{ DOMAIN_PRIMARY }}` | Public domain |
| `server.status_codes.default` | `[200, 301, 302, 405]` | Expected HTTP codes for health check (405 because Fider returns 405 on HEAD requests to `/`) |

## References

- [Fider Hosting Guide](https://getfider.com/docs/hosting)
- [Fider GitHub](https://github.com/getfider/fider)
