# Digital Office

## Purpose

A digital administration and documentation platform for structured organizations.

## Target Audience

Public institutions and administrative bodies modernizing document management and collaboration.

## Included Components

This bundle activates the following Infinito.Nexus roles:

- web-app-nextcloud
- web-app-openproject
- web-app-mediawiki
- web-app-keycloak
- svc-prx-openresty

## Architecture Overview

All services are deployed behind a reverse proxy and share a unified authentication layer where applicable.
The inventory defines a single default host named 'server' and activates roles declaratively via group names.
