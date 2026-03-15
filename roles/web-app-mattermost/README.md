# web-app-mattermost

Deploys [Mattermost Team Edition](https://mattermost.com/) — an open-source, self-hosted team messaging platform — as part of the Infinito.Nexus stack.

## Features

- Single-container deployment via Docker Compose
- PostgreSQL database (MySQL/MariaDB not supported since Mattermost v8+)
- SSO via Keycloak using the GitLab OAuth2 provider (see note below)
- Email notifications via Mailu (optional)
- Persistent storage for config, data, logs, and plugins
- Accessible at `https://chat.<your-domain>`

## SSO / Authentication

Mattermost **Team Edition** does not support native OIDC (`MM_OPENIDSETTINGS_*`) or LDAP — both are Enterprise-only features.

The workaround used here is the **GitLab OAuth2 provider** (`MM_GITLABSETTINGS_*`), which is generic enough to work with any OIDC-compatible identity provider including Keycloak. This provides true SSO: user accounts are automatically created in Mattermost on first login.

The login button in the UI will read "GitLab". This is a cosmetic limitation of Team Edition — the underlying auth flow is standard OAuth2/OIDC against Keycloak.

To enable SSO, set `compose.services.oidc.enabled: true` (the default) in your inventory and ensure `OIDC.CLIENT.SECRET` is configured.

## Bootstrap

On first deploy, the role automatically:

1. Creates the system administrator account
2. Creates a default team named `main`
3. Adds the administrator to the default team

## Configuration

Key settings in `config/main.yml`:

| Key | Default | Description |
|-----|---------|-------------|
| `compose.services.oidc.enabled` | `true` | Enable Keycloak SSO via GitLab OAuth2 |
| `compose.services.database.type` | `postgres` | Database engine (postgres only) |
| `compose.services.mattermost.version` | `latest` | Docker image tag |
| `server.domains.canonical` | `chat.{{ DOMAIN_PRIMARY }}` | Public domain |

## References

- [Mattermost Docker Install](https://docs.mattermost.com/install/install-docker.html)
- [Mattermost Configuration Settings](https://docs.mattermost.com/configure/configuration-settings.html)
- [GitLab SSO in Mattermost](https://docs.mattermost.com/deployment/sso-gitlab.html)
