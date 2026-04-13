from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cli.meta.applications.resolution.services.resolver import (
    ServicesResolver,
    resolve_direct_service_roles_from_config,
)


_MINIMAL_SERVICE_REGISTRY = {
    "ldap": {"role": "svc-db-openldap"},
    "oidc": {"role": "web-app-keycloak"},
    "matomo": {"role": "web-app-matomo"},
    "mariadb": {"role": "svc-db-mariadb"},
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
                    "mariadb": {"enabled": True, "shared": True},
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
    def _mk_role(
        self,
        root: Path,
        role: str,
        *,
        config: str = "compose: {}\n",
        meta: str | None = None,
    ) -> None:
        role_dir = root / "roles" / role
        (role_dir / "config").mkdir(parents=True, exist_ok=True)
        (role_dir / "vars").mkdir(parents=True, exist_ok=True)
        (role_dir / "config" / "main.yml").write_text(config, encoding="utf-8")
        (role_dir / "vars" / "main.yml").write_text(
            f"application_id: {role}\n",
            encoding="utf-8",
        )
        if meta is not None:
            (role_dir / "meta").mkdir(parents=True, exist_ok=True)
            (role_dir / "meta" / "main.yml").write_text(meta, encoding="utf-8")

    def test_transitive_bfs_uses_role_local_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "roles").mkdir()

            self._mk_role(
                root,
                "web-app-app",
                config=(
                    "compose:\n"
                    "  services:\n"
                    "    oidc:\n"
                    "      enabled: true\n"
                    "      shared: true\n"
                ),
            )
            self._mk_role(
                root,
                "web-app-keycloak",
                config=(
                    "compose:\n"
                    "  services:\n"
                    "    keycloak:\n"
                    "      enabled: false\n"
                    "      shared: true\n"
                    "      provides: oidc\n"
                    "    matomo:\n"
                    "      enabled: true\n"
                    "      shared: true\n"
                ),
            )
            self._mk_role(
                root,
                "web-app-matomo",
                config=(
                    "compose:\n"
                    "  services:\n"
                    "    matomo:\n"
                    "      enabled: false\n"
                    "      shared: true\n"
                ),
            )

            resolver = ServicesResolver(root / "roles")
            got = resolver.resolve_transitively("web-app-app")
            self.assertEqual(got, ["web-app-keycloak", "web-app-matomo"])

    def test_repo_pixelfed_includes_dashboard(self) -> None:
        repo_root = Path(__file__).resolve().parents[7]
        resolver = ServicesResolver(repo_root / "roles")

        got = resolver.resolve_transitively("web-app-pixelfed")

        self.assertIn("web-app-dashboard", got)


if __name__ == "__main__":
    unittest.main()
