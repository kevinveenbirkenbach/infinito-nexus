# Community Hub

## Purpose

A federated and community-driven platform for discussion, media sharing, and social networking.

## Target Audience

Associations, NGOs, and online communities looking to build independent digital spaces.

## Included Components

This bundle activates the following Infinito.Nexus roles:

- web-app-discourse
- web-app-mastodon
- web-app-pixelfed
- web-app-peertube
- web-app-friendica
- svc-prx-openresty

## Architecture Overview

All services are deployed behind a reverse proxy and share a unified authentication layer where applicable.
The inventory defines a single default host named 'server' and activates roles declaratively via group names.
