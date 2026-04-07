# Prometheus

Deploys [Prometheus](https://prometheus.io/), an open-source systems monitoring and alerting toolkit, as part of the infinito.nexus stack.

Prometheus is accessible at `prometheus.<domain>` and protected by SSO via Keycloak (oauth2-proxy).

## Features

- Time-series metrics collection and storage
- PromQL query interface via the Prometheus web UI
- SSO authentication via Keycloak (oauth2-proxy)
- Universal logout integration

## Further Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [prom/prometheus Docker image](https://hub.docker.com/r/prom/prometheus)
- Issue #541: Create Prometheus Role
- Issue #542: Integrate Prometheus layer into all applications
