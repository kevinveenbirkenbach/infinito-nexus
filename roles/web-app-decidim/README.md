# Decidim

Deploys [Decidim](https://decidim.org/) — a free, open-source participatory democracy platform — as part of the Infinito.Nexus stack.

## Features

- Custom Docker image built on `ghcr.io/decidim/decidim` with OpenID Connect support
- PostgreSQL database via the shared platform instance
- Redis for caching and Action Cable
- OIDC SSO via Keycloak using `omniauth_openid_connect`
- Accessible at `https://decidim.<your-domain>`

## SSO / Authentication

Decidim's base image does not include an OpenID Connect OmniAuth strategy. This role builds a custom image that:

- Installs the `omniauth_openid_connect` gem via Bundler
- Patches `secrets.yml` to expose the OIDC provider configuration per environment
- Patches `omniauth.rb` to register the provider using env vars at runtime
- Patches `omniauth_helper.rb` to return the correct icon

Credentials (`client_id`, `client_secret`, `issuer`) are read from env vars at runtime — never stored in the database — to avoid `ActiveSupport::MessageEncryptor::InvalidMessage` errors on container rebuild.

To enable SSO, set `compose.services.oidc.enabled: true` in your inventory.

## Configuration

Key settings in `config/main.yml`:

| Key | Default | Description |
|-----|---------|-------------|
| `compose.services.oidc.enabled` | `true` | Enable Keycloak SSO via OpenID Connect |
| `compose.services.postgres.shared` | `true` | Use the shared PostgreSQL service |
| `server.domains.canonical` | `decidim.{{ DOMAIN_PRIMARY }}` | Public domain |

## References

- [Decidim documentation](https://docs.decidim.org/)
- [Decidim Docker image](https://ghcr.io/decidim/decidim)
- [omniauth_openid_connect](https://github.com/omniauth/omniauth_openid_connect)
