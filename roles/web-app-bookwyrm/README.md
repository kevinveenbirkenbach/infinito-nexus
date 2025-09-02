# BookWyrm

## Description

Host your own social reading platform with **BookWyrm**. This role deploys BookWyrm via Docker Compose, wires domains and ports, and offers optional OIDC integration so your readers can sign in through your central identity provider.

## Overview

This role provisions a BookWyrm application stack with Docker. It supports PostgreSQL and Redis, sets sensible environment defaults, and exposes an application container plus a dedicated Celery worker. A reverse proxy (provided elsewhere in your stack) fronts the service for public access.

## Features

- **Fully Dockerized Deployment:** Builds and runs BookWyrm containers (app + worker) using Docker Compose.
- **Production-friendly Settings:** Environment templating for database, Redis, and security-relevant settings (e.g., `SECRET_KEY`).
- **Optional OIDC:** Can integrate with your OIDC provider (e.g., Keycloak) directly or behind oauth2-proxy (depending on your flavor).
- **Volumes for Data & Media:** Persistent volumes for BookWyrm data and media assets.
- **Redis & Celery Worker:** Background tasks processed by Celery; Redis used for broker and cache.
- **Desktop Integration Hooks:** Compatible with your Web App Desktop listing when the role includes this README.
- **Matomo/CSS/Desktop Flags:** Standard feature flags are available for consistent theming/analytics across apps in your ecosystem.

## Further Resources

- [BookWyrm (GitHub)](https://github.com/bookwyrm-social/bookwyrm)
- [BookWyrm Documentation](https://docs.joinbookwyrm.com/)
- [OpenID Connect (Wikipedia)](https://en.wikipedia.org/wiki/OpenID_Connect)
