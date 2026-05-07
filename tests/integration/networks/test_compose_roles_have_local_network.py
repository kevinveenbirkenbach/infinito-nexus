"""Per req-009: every role that ships a Compose template MUST declare its
own local subnet under ``meta/server.yml.networks.local.subnet``."""

from __future__ import annotations

import glob
import unittest
from pathlib import Path

import yaml


class TestComposeRolesHaveLocalNetwork(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from . import PROJECT_ROOT

        cls.repo_root = str(PROJECT_ROOT)
        cls.roles_dir = str(PROJECT_ROOT / "roles")

    def test_every_compose_role_with_application_id_has_local_network(self):
        missing = []

        for role_path in sorted(glob.glob(str(Path(self.roles_dir) / "*"))):
            if not Path(role_path).is_dir():
                continue

            role_name = Path(role_path).name
            compose_template = str(Path(role_path) / "templates" / "compose.yml.j2")
            if not Path(compose_template).is_file():
                continue

            vars_file = str(Path(role_path) / "vars" / "main.yml")
            if not Path(vars_file).is_file():
                continue

            with Path(vars_file).open(encoding="utf-8") as f:
                vars_data = yaml.safe_load(f) or {}
            application_id = vars_data.get("application_id")
            if not application_id:
                continue

            server_file = str(Path(role_path) / "meta" / "server.yml")
            subnet = None
            if Path(server_file).is_file():
                with Path(server_file).open(encoding="utf-8") as f:
                    server_data = yaml.safe_load(f) or {}
                networks = server_data.get("networks") or {}
                local = networks.get("local") if isinstance(networks, dict) else None
                if isinstance(local, dict):
                    subnet = local.get("subnet")

            if not subnet:
                missing.append((role_name, application_id))

        if missing:
            details = "\n".join(
                f"  - role '{role}' (application_id='{app_id}')"
                for role, app_id in missing
            )
            self.fail(
                "The following roles ship a templates/compose.yml.j2 and define "
                "an application_id but have no networks.local.subnet entry in "
                "meta/server.yml (per req-009):\n" + details
            )


if __name__ == "__main__":
    unittest.main()
