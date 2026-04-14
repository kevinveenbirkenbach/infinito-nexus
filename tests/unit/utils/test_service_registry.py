from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from utils.service_registry import (
    ServiceRegistryError,
    build_service_registry_from_applications,
    detect_service_bucket,
    detect_service_channel,
    ordered_primary_service_entries,
    resolve_service_dependency_roles_from_config,
)


class TestServiceRegistryDiscovery(unittest.TestCase):
    def test_discovery_reads_provides_canonical_shared_and_enabled(self):
        applications = {
            "web-app-keycloak": {
                "compose": {
                    "services": {
                        "keycloak": {
                            "enabled": False,
                            "shared": True,
                            "provides": "oidc",
                        }
                    }
                }
            },
            "web-svc-cdn": {
                "compose": {
                    "services": {
                        "cdn": {"enabled": False, "shared": True},
                        "css": {"enabled": True, "shared": True, "canonical": "cdn"},
                        "javascript": {
                            "enabled": False,
                            "shared": True,
                            "canonical": "cdn",
                        },
                    }
                }
            },
        }

        registry = build_service_registry_from_applications(applications)

        self.assertEqual(registry["oidc"]["role"], "web-app-keycloak")
        self.assertEqual(registry["oidc"]["entity_name"], "keycloak")
        self.assertTrue(registry["oidc"]["shared"])
        self.assertFalse(registry["oidc"]["enabled"])

        self.assertEqual(registry["cdn"]["role"], "web-svc-cdn")
        self.assertNotIn("canonical", registry["cdn"])
        self.assertEqual(registry["css"]["canonical"], "cdn")
        self.assertTrue(registry["css"]["enabled"])
        self.assertTrue(registry["javascript"]["shared"])

    def test_entity_name_derivation_for_relevant_role_prefixes(self):
        applications = {
            "web-app-dashboard": {
                "compose": {
                    "services": {"dashboard": {"enabled": False, "shared": True}}
                }
            },
            "web-svc-file": {
                "compose": {"services": {"file": {"enabled": False, "shared": True}}}
            },
            "svc-db-mariadb": {
                "compose": {"services": {"mariadb": {"enabled": False, "shared": True}}}
            },
            "svc-ai-ollama": {
                "compose": {"services": {"ollama": {"enabled": False, "shared": True}}}
            },
        }

        registry = build_service_registry_from_applications(applications)

        self.assertIn("dashboard", registry)
        self.assertIn("file", registry)
        self.assertIn("mariadb", registry)
        self.assertIn("ollama", registry)
        self.assertEqual(detect_service_channel("web-app-dashboard"), "frontend")
        self.assertEqual(detect_service_channel("svc-db-mariadb"), "backend")
        self.assertEqual(detect_service_bucket("web-app-dashboard"), "web-app")
        self.assertEqual(detect_service_bucket("web-svc-file"), "web-svc")
        self.assertEqual(detect_service_bucket("svc-db-mariadb"), "universal")

    def test_direct_service_resolution_uses_role_local_names(self):
        registry = {
            "ldap": {"role": "svc-db-openldap"},
            "mariadb": {"role": "svc-db-mariadb"},
        }
        config = {
            "compose": {
                "services": {
                    "ldap": {"enabled": True, "shared": True},
                    "mariadb": {"enabled": True, "shared": True},
                    "ignored": {"enabled": True, "shared": False},
                }
            }
        }

        self.assertEqual(
            resolve_service_dependency_roles_from_config(config, registry),
            ["svc-db-openldap", "svc-db-mariadb"],
        )


class TestServiceRegistryOrdering(unittest.TestCase):
    def _mk_role(
        self,
        root: Path,
        role: str,
        config: str,
        *,
        run_after: list[str] | None = None,
    ) -> None:
        role_dir = root / role
        (role_dir / "config").mkdir(parents=True, exist_ok=True)
        (role_dir / "config" / "main.yml").write_text(config, encoding="utf-8")
        (role_dir / "meta").mkdir(parents=True, exist_ok=True)
        meta_lines = ["galaxy_info:"]
        if run_after is not None:
            meta_lines.append("  run_after:")
            for item in run_after:
                meta_lines.append(f"    - {item}")
        else:
            meta_lines.append("  run_after: []")
        (role_dir / "meta" / "main.yml").write_text(
            "\n".join(meta_lines) + "\n",
            encoding="utf-8",
        )

    def test_ordered_entries_follow_bucket_order_and_run_after(self):
        registry = {
            "mariadb": {
                "role": "svc-db-mariadb",
                "bucket": "universal",
                "deploy_type": "universal",
            },
            "file": {
                "role": "web-svc-file",
                "bucket": "web-svc",
                "deploy_type": "server",
            },
            "asset": {
                "role": "web-svc-asset",
                "bucket": "web-svc",
                "deploy_type": "server",
            },
            "matomo": {
                "role": "web-app-matomo",
                "bucket": "web-app",
                "deploy_type": "server",
            },
            "dashboard": {
                "role": "web-app-dashboard",
                "bucket": "web-app",
                "deploy_type": "server",
            },
        }

        with tempfile.TemporaryDirectory() as td:
            roles_dir = Path(td)
            self._mk_role(
                roles_dir,
                "svc-db-mariadb",
                "compose:\n  services:\n    mariadb:\n      enabled: false\n      shared: true\n",
            )
            self._mk_role(
                roles_dir,
                "web-svc-file",
                "compose:\n  services:\n    file:\n      enabled: false\n      shared: true\n",
            )
            self._mk_role(
                roles_dir,
                "web-svc-asset",
                "compose:\n  services:\n    asset:\n      enabled: false\n      shared: true\n",
                run_after=["web-svc-file"],
            )
            self._mk_role(
                roles_dir,
                "web-app-matomo",
                "compose:\n  services:\n    matomo:\n      enabled: false\n      shared: true\n",
            )
            self._mk_role(
                roles_dir,
                "web-app-dashboard",
                "compose:\n  services:\n    dashboard:\n      enabled: false\n      shared: true\n",
                run_after=["web-app-matomo"],
            )

            ordered = ordered_primary_service_entries(registry, roles_dir)

        self.assertEqual(
            [entry["role"] for entry in ordered],
            [
                "svc-db-mariadb",
                "web-svc-file",
                "web-svc-asset",
                "web-app-matomo",
                "web-app-dashboard",
            ],
        )

    def test_cross_type_run_after_fails_hard(self):
        registry = {
            "file": {
                "role": "web-svc-file",
                "bucket": "web-svc",
                "deploy_type": "server",
            },
            "mail": {
                "role": "sys-svc-mail",
                "bucket": "universal",
                "deploy_type": "universal",
            },
        }

        with tempfile.TemporaryDirectory() as td:
            roles_dir = Path(td)
            self._mk_role(
                roles_dir,
                "web-svc-file",
                "compose:\n  services:\n    file:\n      enabled: false\n      shared: true\n",
                run_after=["sys-svc-mail"],
            )
            self._mk_role(
                roles_dir,
                "sys-svc-mail",
                "compose:\n  services:\n    mail:\n      enabled: false\n      shared: true\n",
            )

            with self.assertRaises(ServiceRegistryError):
                ordered_primary_service_entries(registry, roles_dir)


if __name__ == "__main__":
    unittest.main()
