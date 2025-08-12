# cmp-docker-oauth2

This Ansible role enhances a Docker Compose application by conditionally enabling OAuth2-based authentication. It ensures that the `docker-compose` role is always loaded, and if the application has OAuth2 support enabled via `features.oauth2`, it also configures the OAuth2 proxy.

## Features

- Loads the `docker-compose` role
- Conditionally configures OAuth2 reverse proxy via `web-app-oauth2-proxy`
- Supports OIDC providers like Keycloak
- Application-driven behavior via `features.oauth2` in the configuration

## License

Infinito.Nexus NonCommercial License (CNCL)
See: [https://s.infinito.nexus/license](https://s.infinito.nexus/license)

## Author

Kevin Veen-Birkenbach
Consulting & Coaching Solutions
[https://www.veen.world](https://www.veen.world)