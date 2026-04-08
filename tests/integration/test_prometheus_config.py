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
            p for p in sorted(glob.glob(pattern))
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


if __name__ == "__main__":
    unittest.main()
