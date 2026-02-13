# Power Sale Package

## Purpose

A high-performance e-commerce stack optimized for conversion and analytics.

## Target Audience

Online retailers and businesses operating digital storefronts.

## Included Components

This bundle activates the following Infinito.Nexus roles:

- web-app-magento
- web-app-shopware
- web-app-matomo
- web-app-keycloak
- svc-prx-openresty

## Architecture Overview

All services are deployed behind a reverse proxy and share a unified authentication layer where applicable.
The inventory defines a single default host named 'server' and activates roles declaratively via group names.
