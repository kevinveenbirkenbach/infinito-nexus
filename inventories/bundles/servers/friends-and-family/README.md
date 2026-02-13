# Friends & Family

## Purpose

A simple and secure private infrastructure for families and small trusted groups.

## Target Audience

Households and small communities sharing files, communication, and media.

## Included Components

This bundle activates the following Infinito.Nexus roles:

- web-app-nextcloud
- web-svc-onlyoffice
- web-app-matrix
- web-app-keycloak
- svc-prx-openresty

## Architecture Overview

All services are deployed behind a reverse proxy and share a unified authentication layer where applicable.
The inventory defines a single default host named 'server' and activates roles declaratively via group names.
