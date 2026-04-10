import glob
import unittest
import yaml
from pathlib import Path


PROMETHEUS_APP_ID = "web-app-prometheus"


def _load_config(file_path: str) -> dict:
    return yaml.safe_load(Path(file_path).read_text(encoding="utf-8")) or {}


class TestPrometheusServicePresence(unittest.TestCase):
    """
    All web-app-* and web-svc-* roles (except web-app-prometheus itself) must
    declare the shared prometheus service in their compose.services section:

        prometheus:
          enabled: true
          shared: true

    This enables the prometheus role to discover them via the
    service_should_load lookup plugin.
    """

    def _web_role_configs(self):
        roles_dir = Path(__file__).resolve().parent.parent.parent / "roles"
        pattern = str(roles_dir / "*" / "config" / "main.yml")
        return [
            p
            for p in sorted(glob.glob(pattern))
            if (
                Path(p).parts[-3].startswith(("web-app-", "web-svc-"))
                and Path(p).parts[-3] != PROMETHEUS_APP_ID
            )
        ]

    def test_all_web_roles_have_prometheus_service(self):
        """Every web-app-* and web-svc-* role must have compose.services.prometheus."""
        configs = self._web_role_configs()
        self.assertTrue(configs, "No web-app-*/web-svc-* config/main.yml files found")

        errors = []
        for file_path in configs:
            role_name = Path(file_path).parts[-3]
            try:
                cfg = _load_config(file_path)
            except yaml.YAMLError as exc:
                errors.append(f"{role_name}: YAML parse error: {exc}")
                continue

            services = (cfg.get("compose") or {}).get("services") or {}
            prom = services.get("prometheus")

            if prom is None:
                errors.append(
                    f"{role_name}: compose.services.prometheus is missing. "
                    f"Add:\n    prometheus:\n      enabled: true\n      shared: true"
                )
                continue

            if not isinstance(prom, dict):
                errors.append(
                    f"{role_name}: compose.services.prometheus must be a mapping, got {type(prom).__name__}"
                )
                continue

            if prom.get("enabled") is not True:
                errors.append(
                    f"{role_name}: compose.services.prometheus.enabled must be true, "
                    f"got {prom.get('enabled')!r}"
                )

            if prom.get("shared") is not True:
                errors.append(
                    f"{role_name}: compose.services.prometheus.shared must be true, "
                    f"got {prom.get('shared')!r}"
                )

        if errors:
            self.fail(
                f"Prometheus service configuration violations ({len(errors)}):\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

    def test_prometheus_role_has_image_config(self):
        """web-app-prometheus must define image, version, and name for its service."""
        roles_dir = Path(__file__).resolve().parent.parent.parent / "roles"
        config_path = roles_dir / PROMETHEUS_APP_ID / "config" / "main.yml"

        self.assertTrue(config_path.exists(), f"Missing: {config_path}")

        cfg = _load_config(str(config_path))
        svc = (cfg.get("compose") or {}).get("services") or {}
        prom = svc.get("prometheus") or {}

        for key in ("image", "version", "name"):
            with self.subTest(key=key):
                self.assertIn(
                    key,
                    prom,
                    f"web-app-prometheus: compose.services.prometheus.{key} is not set",
                )
                self.assertTrue(
                    prom[key],
                    f"web-app-prometheus: compose.services.prometheus.{key} must not be empty",
                )


class TestPrometheusNginxEndpoints(unittest.TestCase):
    """
    The shared nginx vhost template must expose /healthz/live and /healthz/ready.
    The /metricz endpoint and log_by_lua_block live in the prometheus role's own
    location.conf.j2 (included conditionally when prometheus is enabled), following
    KISS and SRP principles per Kevin's review of PR #144.
    """

    def _basic_conf_path(self):
        return (
            Path(__file__).resolve().parent.parent.parent
            / "roles"
            / "sys-svc-proxy"
            / "templates"
            / "vhost"
            / "basic.conf.j2"
        )

    def _location_conf_path(self):
        return (
            Path(__file__).resolve().parent.parent.parent
            / "roles"
            / "web-app-prometheus"
            / "templates"
            / "location.conf.j2"
        )

    def test_basic_conf_has_health_endpoints(self):
        """basic.conf.j2 must define /healthz/live and /healthz/ready."""
        conf_path = self._basic_conf_path()
        self.assertTrue(conf_path.exists(), f"Missing: {conf_path}")
        content = conf_path.read_text(encoding="utf-8")

        for endpoint in ("/healthz/live", "/healthz/ready"):
            with self.subTest(endpoint=endpoint):
                self.assertIn(
                    f"location = {endpoint}",
                    content,
                    f"basic.conf.j2 is missing 'location = {endpoint}'",
                )

    def test_basic_conf_live_probe_uses_lua(self):
        """basic.conf.j2 /healthz/live must use Lua to check backend health, not a static return."""
        content = self._basic_conf_path().read_text(encoding="utf-8")
        self.assertIn(
            "content_by_lua_block",
            content,
            "/healthz/live must use content_by_lua_block to check backend reachability",
        )
        self.assertNotIn(
            'return 200 "live',
            content,
            "/healthz/live must NOT be a static return 200 — it must check backend health",
        )

    def test_basic_conf_includes_prometheus_location_template(self):
        """basic.conf.j2 must conditionally include the prometheus location template.

        The condition covers two cases:
          - Regular apps:           compose.services.prometheus.enabled = true
          - web-app-prometheus itself: compose.services.prometheus.name is set
            (its domain is the central /metricz scrape target; there is no 'enabled'
            flag because the 'prometheus' key describes the container, not the integration).
        """
        content = self._basic_conf_path().read_text(encoding="utf-8")
        self.assertIn(
            "roles/web-app-prometheus/templates/location.conf.j2",
            content,
            "basic.conf.j2 must include roles/web-app-prometheus/templates/location.conf.j2 "
            "for prometheus-enabled apps (SRP — per Kevin's review of PR #144)",
        )
        self.assertIn(
            "compose.services.prometheus.name",
            content,
            "basic.conf.j2 condition must also check compose.services.prometheus.name "
            "so that the prometheus app's own domain gets location = /metricz",
        )

    def test_location_conf_has_metricz_endpoint(self):
        """/metricz must be defined in the prometheus role's location.conf.j2, not basic.conf.j2."""
        loc_path = self._location_conf_path()
        self.assertTrue(loc_path.exists(), f"Missing: {loc_path}")
        content = loc_path.read_text(encoding="utf-8")
        self.assertIn(
            "location = /metricz",
            content,
            "location.conf.j2 must define 'location = /metricz'",
        )

    def test_location_conf_metricz_exposes_stack_up_gauge(self):
        """/metricz must update the stack_up gauge before collecting metrics."""
        content = self._location_conf_path().read_text(encoding="utf-8")
        self.assertIn(
            "metric_stack_up",
            content,
            "/metricz in location.conf.j2 must set metric_stack_up gauge "
            "(per Kevin's review: 'if healthy then up otherwise not')",
        )

    def test_location_conf_metricz_stack_up_checks_docker_health(self):
        """/metricz stack_up gauge must reflect Docker HEALTHCHECK, not just HTTP reachability.

        Kevin's review: 'if healthy then up otherwise not' — the gauge must use the
        same Docker-socket-backed health_containers dict as /healthz/live so that a
        container with a failing HEALTHCHECK shows nginx_stack_up = 0 in Prometheus.
        """
        content = self._location_conf_path().read_text(encoding="utf-8")
        self.assertIn(
            "health_containers",
            content,
            "/metricz in location.conf.j2 must check health_containers shared dict "
            "so metric_stack_up reflects Docker HEALTHCHECK state, not just HTTP reachability "
            "(Kevin's review: 'if healthy then up otherwise not')",
        )

    def test_location_conf_has_lua_metrics_collection(self):
        """location.conf.j2 must collect per-request metrics via log_by_lua_block."""
        content = self._location_conf_path().read_text(encoding="utf-8")
        self.assertIn(
            "log_by_lua_block",
            content,
            "location.conf.j2 must include log_by_lua_block for per-request nginx metrics",
        )

    def test_location_conf_metrics_have_app_label(self):
        """All nginx metrics in location.conf.j2 must carry the 'app' label (task AC: labels MUST include app)."""
        content = self._location_conf_path().read_text(encoding="utf-8")
        self.assertIn(
            "app_id",
            content,
            "location.conf.j2 must use ngx.var.app_id so all metrics carry the 'app' label "
            "(required by task AC: labels MUST include app, domain/vhost)",
        )

    def test_location_conf_collects_tls_metrics(self):
        """location.conf.j2 must collect TLS handshake metrics (task AC: TLS/HTTPS metrics if available)."""
        content = self._location_conf_path().read_text(encoding="utf-8")
        self.assertIn(
            "ssl_protocol",
            content,
            "location.conf.j2 must collect TLS metrics via ngx.var.ssl_protocol "
            "(task AC: TLS/HTTPS-related metrics if available)",
        )

    def test_basic_conf_sets_app_id_variable(self):
        """basic.conf.j2 must set $app_id so Lua blocks can attach the 'app' label."""
        content = self._basic_conf_path().read_text(encoding="utf-8")
        self.assertIn(
            "$app_id",
            content,
            "basic.conf.j2 must set the $app_id nginx variable (used by location.conf.j2 "
            "to attach the 'app' label to all metrics)",
        )

    def test_alertmanager_templates_exist(self):
        """web-app-prometheus must have alertmanager.yml.j2 and alert_rules.yml.j2."""
        roles_dir = Path(__file__).resolve().parent.parent.parent / "roles"
        for template in ("alertmanager.yml.j2", "alert_rules.yml.j2"):
            with self.subTest(template=template):
                path = roles_dir / PROMETHEUS_APP_ID / "templates" / template
                self.assertTrue(
                    path.exists(),
                    f"Missing alertmanager template: {path}",
                )

    def test_alertmanager_supports_telegram(self):
        """alertmanager.yml.j2 must support Telegram notifications (task AC: communication channels)."""
        roles_dir = Path(__file__).resolve().parent.parent.parent / "roles"
        content = (
            roles_dir / PROMETHEUS_APP_ID / "templates" / "alertmanager.yml.j2"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "telegram_configs",
            content,
            "alertmanager.yml.j2 must include telegram_configs for Telegram notifications "
            "(task AC: Telegram or preferred Matrix Message)",
        )

    def test_alertmanager_supports_mattermost(self):
        """alertmanager.yml.j2 must support Mattermost webhook notifications (task AC: communication channels)."""
        roles_dir = Path(__file__).resolve().parent.parent.parent / "roles"
        content = (
            roles_dir / PROMETHEUS_APP_ID / "templates" / "alertmanager.yml.j2"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "ALERTMANAGER_MATTERMOST_WEBHOOK_URL",
            content,
            "alertmanager.yml.j2 must include Mattermost webhook config (task AC: Mattermost notification)",
        )


class TestDockerHealthCheck(unittest.TestCase):
    """
    /healthz/live must check Docker container health in addition to HTTP reachability.
    Kevin's review: HTTP-reachability alone is insufficient — a container can be
    "running" in Docker while its HEALTHCHECK has flipped to "unhealthy".
    """

    def _nginx_conf_path(self):
        return (
            Path(__file__).resolve().parent.parent.parent
            / "roles"
            / "sys-svc-webserver-core"
            / "templates"
            / "nginx.conf.j2"
        )

    def _basic_conf_path(self):
        return (
            Path(__file__).resolve().parent.parent.parent
            / "roles"
            / "sys-svc-proxy"
            / "templates"
            / "vhost"
            / "basic.conf.j2"
        )

    def _openresty_compose_path(self):
        return (
            Path(__file__).resolve().parent.parent.parent
            / "roles"
            / "svc-prx-openresty"
            / "templates"
            / "compose.yml.j2"
        )

    def test_nginx_conf_has_health_containers_dict(self):
        """nginx.conf.j2 must declare lua_shared_dict health_containers for Docker state caching."""
        content = self._nginx_conf_path().read_text(encoding="utf-8")
        self.assertIn(
            "lua_shared_dict health_containers",
            content,
            "nginx.conf.j2 must declare lua_shared_dict health_containers "
            "(used by /healthz/live to cache Docker container health state)",
        )

    def test_nginx_conf_polls_docker_socket(self):
        """nginx.conf.j2 must poll the Docker Unix socket to populate health_containers."""
        content = self._nginx_conf_path().read_text(encoding="utf-8")
        self.assertIn(
            "docker.sock",
            content,
            "nginx.conf.j2 must connect to /var/run/docker.sock to query container health",
        )
        self.assertIn(
            "poll_docker_health",
            content,
            "nginx.conf.j2 must define a poll_docker_health timer function",
        )

    def test_nginx_conf_timer_runs_at_startup_and_periodically(self):
        """nginx.conf.j2 must seed the dict immediately (timer.at) and refresh periodically (timer.every)."""
        content = self._nginx_conf_path().read_text(encoding="utf-8")
        self.assertIn(
            "ngx.timer.at",
            content,
            "nginx.conf.j2 must use ngx.timer.at(0, ...) to seed health_containers at startup",
        )
        self.assertIn(
            "ngx.timer.every",
            content,
            "nginx.conf.j2 must use ngx.timer.every to refresh health_containers periodically",
        )

    def test_basic_conf_has_container_name_variable(self):
        """basic.conf.j2 must set $container_name so /healthz/live can look up Docker state."""
        content = self._basic_conf_path().read_text(encoding="utf-8")
        self.assertIn(
            "$container_name",
            content,
            "basic.conf.j2 must set the $container_name nginx variable "
            "(used by /healthz/live to consult the health_containers shared dict)",
        )

    def test_basic_conf_live_probe_checks_docker_health(self):
        """/healthz/live must consult health_containers before the HTTP sub-request."""
        content = self._basic_conf_path().read_text(encoding="utf-8")
        self.assertIn(
            "health_containers",
            content,
            "/healthz/live in basic.conf.j2 must read health_containers shared dict "
            "(Docker health check per Kevin's review — HTTP-only is insufficient)",
        )

    def test_openresty_compose_mounts_docker_socket(self):
        """OpenResty compose must mount /var/run/docker.sock read-only for the Lua health timer."""
        content = self._openresty_compose_path().read_text(encoding="utf-8")
        self.assertIn(
            "/var/run/docker.sock",
            content,
            "svc-prx-openresty compose.yml.j2 must mount /var/run/docker.sock:ro "
            "so the Lua background timer can query Docker container health",
        )


class TestNativeAppMetrics(unittest.TestCase):
    """
    Applications that provide native Prometheus metrics MUST have a scrape job
    in prometheus.yml.j2 (task AC: expose /metrics for apps that support it).
    """

    def _prometheus_yml_path(self):
        return (
            Path(__file__).resolve().parent.parent.parent
            / "roles"
            / "web-app-prometheus"
            / "templates"
            / "prometheus.yml.j2"
        )

    def test_prometheus_yml_has_gitea_native_metrics_job(self):
        """prometheus.yml.j2 must include a Gitea native metrics scrape job."""
        content = self._prometheus_yml_path().read_text(encoding="utf-8")
        self.assertIn(
            'job_name: "gitea"',
            content,
            "prometheus.yml.j2 must define a 'gitea' scrape job for native Go/app metrics "
            "(task AC: apps that support metrics MUST expose /metrics)",
        )

    def test_prometheus_gitea_job_uses_metrics_path(self):
        """The Gitea scrape job must use metrics_path: /metrics."""
        content = self._prometheus_yml_path().read_text(encoding="utf-8")
        self.assertIn(
            "metrics_path: /metrics",
            content,
            "prometheus.yml.j2 Gitea job must set metrics_path: /metrics",
        )


if __name__ == "__main__":
    unittest.main()
