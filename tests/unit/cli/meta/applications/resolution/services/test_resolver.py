# tests/unit/cli/meta/applications/resolution/services/test_resolver.py
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from cli.meta.applications.resolution.services.errors import ServicesResolutionError
from cli.meta.applications.resolution.services.resolver import (
    ServicesResolver,
    resolve_direct_service_roles_from_config,
)

_MINIMAL_SERVICE_REGISTRY = {
    "ldap": {"role": "svc-db-openldap"},
    "oidc": {"role": "web-app-keycloak"},
    "matomo": {"role": "web-app-matomo"},
    "database": {"role_template": "svc-db-{type}"},
    "dashboard": {"role": "web-app-dashboard"},
}


class TestServicesResolverDirect(unittest.TestCase):
    def test_direct_mapping_shared_services(self) -> None:
        cfg = {
            "compose": {
                "services": {
                    "ldap": {"enabled": True, "shared": True},
                    "oidc": {"enabled": True, "shared": True},
                    "matomo": {"enabled": True, "shared": True},
                    "database": {"enabled": True, "shared": True, "type": "mariadb"},
                    "dashboard": {"enabled": True, "shared": True},
                }
            }
        }
        roles = resolve_direct_service_roles_from_config(cfg, _MINIMAL_SERVICE_REGISTRY)
        self.assertEqual(
            roles,
            [
                "svc-db-openldap",
                "web-app-keycloak",
                "web-app-matomo",
                "svc-db-mariadb",
                "web-app-dashboard",
            ],
        )

    def test_database_missing_type_raises(self) -> None:
        cfg = {
            "compose": {
                "services": {
                    "database": {"enabled": True, "shared": True},
                }
            }
        }
        with self.assertRaises(ServicesResolutionError):
            resolve_direct_service_roles_from_config(cfg, _MINIMAL_SERVICE_REGISTRY)

    def test_non_shared_not_included(self) -> None:
        cfg = {
            "compose": {
                "services": {
                    "ldap": {"enabled": True, "shared": False},
                    "dashboard": {"enabled": True, "shared": False},
                }
            }
        }
        roles = resolve_direct_service_roles_from_config(cfg, _MINIMAL_SERVICE_REGISTRY)
        self.assertEqual(roles, [])


class TestServicesResolverTransitive(unittest.TestCase):
    def _mk_role(self, root: Path, role: str, config: str | None = None) -> None:
        role_dir = root / "roles" / role
        (role_dir / "config").mkdir(parents=True, exist_ok=True)
        if config is not None:
            (role_dir / "config" / "main.yml").write_text(config, encoding="utf-8")

    def _mk_services_file(self, root: Path, mapping: dict) -> Path:
        path = root / "20_services.yml"
        path.write_text(yaml.dump({"SERVICE_REGISTRY": mapping}), encoding="utf-8")
        return path

    def test_transitive_bfs(self) -> None:
        # app -> oidc(shared) => keycloak
        # keycloak config -> matomo(shared) => matomo
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "roles").mkdir()

            services_file = self._mk_services_file(
                root,
                {
                    "oidc": {"role": "web-app-keycloak", "type": "frontend"},
                    "matomo": {"role": "web-app-matomo", "type": "frontend"},
                },
            )

            self._mk_role(
                root,
                "web-app-app",
                "compose:\n  services:\n    oidc:\n      enabled: true\n      shared: true\n",
            )
            self._mk_role(
                root,
                "web-app-keycloak",
                "compose:\n  services:\n    matomo:\n      enabled: true\n      shared: true\n",
            )
            self._mk_role(root, "web-app-matomo", "compose: {}\n")

            r = ServicesResolver(root / "roles", services_file=services_file)
            got = r.resolve_transitively("web-app-app")
            self.assertEqual(got, ["web-app-keycloak", "web-app-matomo"])

    def test_repo_pixelfed_includes_dashboard(self) -> None:
        repo_root = Path(__file__).resolve().parents[7]
        r = ServicesResolver(repo_root / "roles")

        got = r.resolve_transitively("web-app-pixelfed")

        self.assertIn("web-app-dashboard", got)


if __name__ == "__main__":
    unittest.main()
