# Todos
- Implement [OIDC](https://www.talkingquickly.co.uk/gitea-sso-with-keycloak-openldap-openid-connect)
- Enable native Prometheus metrics scraping: set `GITEA__metrics__ENABLED=true` and `GITEA__metrics__TOKEN` in `env.j2`, change `prometheus.yml.j2` target to internal container port to bypass nginx/OAuth2 proxy, store token via `lookup('config', application_id, 'native_metrics.token')`
