# Prometheus

## Description

[Prometheus](https://prometheus.io/) is an open-source systems monitoring and alerting toolkit that collects and stores time-series metrics and provides a powerful query language (PromQL).

## Overview

This role deploys Prometheus as part of the Infinito.Nexus stack using Docker Compose. It exposes the Prometheus web UI at `prometheus.<domain>` and protects it with SSO via Keycloak using oauth2-proxy. Universal logout is integrated for session termination.

## Features

- **Time-series metrics:** Collects and stores time-series data from configured targets.
- **PromQL interface:** Query and explore metrics via the Prometheus web UI.
- **SSO authentication:** Access is protected by Keycloak via oauth2-proxy.
- **Universal logout:** Integrated session termination across the stack.

## Further resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [prom/prometheus Docker image](https://hub.docker.com/r/prom/prometheus)

## Credits

Developed and maintained by **Kevin Veen-Birkenbach**.
Learn more at [veen.world](https://www.veen.world).
Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code).
Licensed under the [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license).
