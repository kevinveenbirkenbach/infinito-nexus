# LibreTranslate

This role deploys **LibreTranslate** as a containerized web service using Docker Compose.
It is designed to integrate seamlessly into the Infinito.Nexus stack, including optional
Redis and database backends, CSP handling, and analytics integration.

## Description

LibreTranslate is an open-source machine translation API that can be self-hosted.
This role provides a standardized, reproducible deployment with optional extensions
such as Redis caching, database persistence, and Matomo tracking.

The role follows Infinito.Nexus conventions:
- container abstraction (`container`, `compose`)
- centralized configuration via `config/main.yml`
- CSP-aware reverse proxy integration
- optional shared services (database, analytics)

## Overview

- Deployment via Docker Compose
- Stateless by default, with optional stateful backends
- Designed for reverse-proxy setups
- Suitable for internal services, public APIs, or desktop integration
- Compatible with the Infinito.Nexus role and metadata system

## Features

- LibreTranslate service deployment
- Configurable container image and version
- Optional Redis backend
- Optional database backend
- Optional Matomo analytics integration
- CSP configuration support
- Custom JavaScript injection
- Desktop integration toggle
- Health checks via HTTP
- Network and dependency handling via shared system roles

## Configuration

All configuration is handled via `config/main.yml`.

Key sections include:
- `compose.services.libretranslate`: image and version
- `compose.services.redis`: enable Redis backend
- `compose.services.database`: enable database backend
- `compose.services.matomo`: enable analytics
- `server.domains`: canonical and alias domains
- `server.csp`:
