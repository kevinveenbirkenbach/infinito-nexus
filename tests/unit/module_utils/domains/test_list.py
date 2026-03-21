import importlib
import tempfile
import unittest
from pathlib import Path

import yaml
from ansible.errors import AnsibleError

domain_list = importlib.import_module("module_utils.domains.list")


class TestDomainList(unittest.TestCase):
    def write_role(self, roles_dir: Path, role_name: str, app_id: str, config: dict):
        role_dir = roles_dir / role_name
        (role_dir / "vars").mkdir(parents=True, exist_ok=True)
        (role_dir / "config").mkdir(parents=True, exist_ok=True)
        (role_dir / "vars" / "main.yml").write_text(
            yaml.safe_dump({"application_id": app_id}, sort_keys=False),
            encoding="utf-8",
        )
        (role_dir / "config" / "main.yml").write_text(
            yaml.safe_dump(config, sort_keys=False),
            encoding="utf-8",
        )

    def test_list_application_domains_renders_and_flattens_supported_shapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles_dir = Path(tmp) / "roles"
            roles_dir.mkdir()

            self.write_role(
                roles_dir,
                "web-app-dashboard",
                "web-app-dashboard",
                {
                    "server": {
                        "domains": {
                            "canonical": ["dashboard.{{ DOMAIN_PRIMARY }}"],
                            "aliases": ["www.dashboard.{{ DOMAIN_PRIMARY }}"],
                        }
                    }
                },
            )
            self.write_role(
                roles_dir,
                "web-app-minio",
                "web-app-minio",
                {
                    "server": {
                        "domains": {
                            "canonical": {
                                "api": "api.s3.{{ DOMAIN_PRIMARY }}",
                                "console": "console.s3.{{ DOMAIN_PRIMARY }}",
                            },
                            "aliases": [],
                        }
                    }
                },
            )

            domains = domain_list.list_application_domains(
                roles_dir, "infinito.example"
            )

            self.assertEqual(
                domains,
                sorted(
                    [
                        "api.s3.infinito.example",
                        "console.s3.infinito.example",
                        "dashboard.infinito.example",
                        "test.infinito.example",
                        "www.dashboard.infinito.example",
                    ]
                ),
            )

    def test_list_application_domains_includes_derived_test_domain_without_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles_dir = Path(tmp) / "roles"
            roles_dir.mkdir()

            domains = domain_list.list_application_domains(
                roles_dir, "infinito.example"
            )

            self.assertEqual(domains, ["test.infinito.example"])

    def test_list_application_domains_raises_on_collisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles_dir = Path(tmp) / "roles"
            roles_dir.mkdir()

            shared_config = {
                "server": {
                    "domains": {
                        "canonical": ["same.{{ DOMAIN_PRIMARY }}"],
                        "aliases": [],
                    }
                }
            }
            self.write_role(roles_dir, "app-a", "app-a", shared_config)
            self.write_role(roles_dir, "app-b", "app-b", shared_config)

            with self.assertRaises(AnsibleError):
                domain_list.list_application_domains(roles_dir, "infinito.example")


if __name__ == "__main__":
    unittest.main()
