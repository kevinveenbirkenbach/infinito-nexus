# Media Platform

## Purpose

A content publishing and distribution ecosystem for creators and media organizations.

## Target Audience

Bloggers, podcasters, and media companies seeking independent publishing infrastructure.

## Included Components

This bundle activates the following Infinito.Nexus roles:

- web-app-wordpress
- web-app-matomo
- web-app-peertube
- web-app-funkwhale
- svc-prx-openresty

## Architecture Overview

All services are deployed behind a reverse proxy and share a unified authentication layer where applicable.
The inventory defines a single default host named 'server' and activates roles declaratively via group names.
