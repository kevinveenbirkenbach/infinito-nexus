# Enterprise Stack

## Purpose

A professional collaboration and identity management stack for modern organizations.

## Target Audience

Small and medium-sized enterprises that require secure collaboration and centralized authentication.

## Included Components

This bundle activates the following Infinito.Nexus roles:

- web-app-nextcloud
- web-svc-onlyoffice
- web-app-openproject
- web-app-matrix
- web-app-keycloak
- svc-prx-openresty

## Architecture Overview

All services are deployed behind a reverse proxy and share a unified authentication layer where applicable.
The inventory defines a single default host named 'server' and activates roles declaratively via group names.
