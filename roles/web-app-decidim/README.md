# Decidim

Ansible role that deploys [Decidim](https://decidim.org/) as a fully managed
Infinito.Nexus web application.

## What is Decidim?

Decidim is a free, open-source participatory democracy platform used by
municipalities, schools, NGOs, and enterprises to run:

- Public consultations and polls
- Civic budget processes
- Collaborative policy creation
- Community voting and proposal management
- Participatory assemblies

## Architecture

| Component | Purpose |
|-----------|---------|
| `decidim` | Puma application server |
| `sidekiq` | Background workers (emails, exports) |
| `redis` | Sidekiq queue + Action Cable adapter |
| PostgreSQL | Persistent relational storage (shared instance) |
| NGINX | TLS termination and reverse proxy via sys-svc-proxy |

## Requirements

- Infinito.Nexus platform with `sys-stk-full`
- PostgreSQL shared instance
- Redis shared instance
- Keycloak for OIDC SSO (optional)

## Variables

All variables are defined in `vars/main.yml` and follow the platform
lookup plugin conventions.

| Variable | Description |
|----------|-------------|
| `DECIDIM_VERSION` | Decidim Docker image version |
| `DECIDIM_IMAGE` | Decidim Docker image name |
| `DECIDIM_CONTAINER` | Web container name |
| `DECIDIM_SIDEKIQ_CONTAINER` | Sidekiq container name |
| `DECIDIM_SECRET_KEY_BASE` | Rails secret key base |
| `DECIDIM_OIDC_ENABLED` | Enable Keycloak SSO |

## OIDC Setup

Set `compose.services.oidc.enabled: true` in `config/main.yml`.
Ensure Keycloak has a client configured with:
- **Client ID:** `decidim`
- **Valid Redirect URIs:** `https://<domain>/users/auth/openid_connect/callback`

## Deployment

```bash
ansible-playbook playbook.yml --limit <host> --tags web-app-decidim
```

## Testing

E2E tests are in `files/playwright.spec.js`.
Environment variables are templated via `templates/playwright.env.j2`.

## References

- [Decidim documentation](https://docs.decidim.org/)
- [Decidim Docker image](https://hub.docker.com/r/decidim/decidim)
- [Infinito.Nexus CONTRIBUTING.md](../../CONTRIBUTING.md)
