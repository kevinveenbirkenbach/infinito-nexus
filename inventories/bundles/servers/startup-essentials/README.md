# Startup Essentials

## Purpose

A rapid deployment stack for startups building software products and services.

## Target Audience

Founders and development teams needing version control, CI/CD, and secure collaboration.

## Included Components

This bundle activates the following Infinito.Nexus roles:

- web-app-gitea
- web-app-gitlab
- web-app-jenkins
- web-app-matrix
- web-app-keycloak
- svc-prx-openresty

## Architecture Overview

All services are deployed behind a reverse proxy and share a unified authentication layer where applicable.
The inventory defines a single default host named 'server' and activates roles declaratively via group names.
