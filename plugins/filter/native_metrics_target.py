from __future__ import annotations

from ansible.errors import AnsibleFilterError


_HOST = "host.docker.internal"


def native_metrics_target(app_id: str, ports: dict) -> str:
    """Return the internal Prometheus scrape target for a native-metrics app.

    Encapsulates both the Docker-host gateway hostname and the port lookup so
    all app scrape fragments use one consistent expression instead of
    duplicating "host.docker.internal" and the ports dict path.

    Usage in a per-app prometheus.yml.j2 fragment:
      targets: ["{{ native_prometheus_application_id | native_metrics_target(ports) }}"]
    """
    port = (ports.get("localhost") or {}).get("metrics", {}).get(app_id)
    if port is None:
        raise AnsibleFilterError(
            f"native_metrics_target: no ports.localhost.metrics entry for '{app_id}'"
        )
    return f"{_HOST}:{port}"


class FilterModule:
    def filters(self):
        return {"native_metrics_target": native_metrics_target}
