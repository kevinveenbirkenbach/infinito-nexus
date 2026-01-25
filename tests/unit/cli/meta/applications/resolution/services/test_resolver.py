# tests/unit/cli/meta/applications/resolution/services/test_resolver.py
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cli.meta.applications.resolution.services.errors import ServicesResolutionError
from cli.meta.applications.resolution.services.resolver import (
    ServicesResolver,
    resolve_direct_service_roles_from_config,
)


class TestServicesResolverDirect(unittest.TestCase):
    def test_direct_mapping_shared_services_and_desktop(self) -> None:
        cfg = {
            "docker": {
                "services": {
                    "ldap": {"enabled": True, "shared": True},
                    "oidc": {"enabled": True, "shared": True},
                    "matomo": {"enabled": True, "shared": True},
                    "database": {"enabled": True, "shared": True, "type": "mariadb"},
                    "desktop": {"enabled": True},  # shared irrelevant
                }
            }
        }
        roles = resolve_direct_service_roles_from_config(cfg)
        self.assertEqual(
            roles,
            [
                "svc-db-openldap",
                "web-app-keycloak",
                "web-app-matomo",
                "svc-db-mariadb",
                "web-app-desktop",
            ],
        )

    def test_database_missing_type_raises(self) -> None:
        cfg = {
            "docker": {
                "services": {
                    "database": {"enabled": True, "shared": True},
                }
            }
        }
        with self.assertRaises(ServicesResolutionError):
            resolve_direct_service_roles_from_config(cfg)

    def test_non_shared_not_included_except_desktop(self) -> None:
        cfg = {
            "docker": {
                "services": {
                    "ldap": {"enabled": True, "shared": False},
                    "desktop": {"enabled": True},
                }
            }
        }
        roles = resolve_direct_service_roles_from_config(cfg)
        self.assertEqual(roles, ["web-app-desktop"])


class TestServicesResolverTransitive(unittest.TestCase):
    def _mk_role(self, root: Path, role: str, config: str | None = None) -> None:
        role_dir = root / "roles" / role
        (role_dir / "config").mkdir(parents=True, exist_ok=True)
        if config is not None:
            (role_dir / "config" / "main.yml").write_text(config, encoding="utf-8")

    def test_transitive_bfs(self) -> None:
        # app -> oidc(shared) => keycloak
        # keycloak config -> matomo(shared) => matomo
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "roles").mkdir()

            self._mk_role(
                root,
                "web-app-app",
                "docker:\n  services:\n    oidc:\n      enabled: true\n      shared: true\n",
            )
            self._mk_role(
                root,
                "web-app-keycloak",
                "docker:\n  services:\n    matomo:\n      enabled: true\n      shared: true\n",
            )
            self._mk_role(root, "web-app-matomo", "docker: {}\n")

            r = ServicesResolver(root / "roles")
            got = r.resolve_transitively("web-app-app")
            self.assertEqual(got, ["web-app-keycloak", "web-app-matomo"])


if __name__ == "__main__":
    unittest.main()
