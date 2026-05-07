"""Per req-009: every role that ships a Compose template MUST declare its
own local subnet under ``meta/server.yml.networks.local.subnet``."""

from __future__ import annotations

import glob
import os
import unittest


from utils.cache.yaml import load_yaml_any


class TestComposeRolesHaveLocalNetwork(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.dirname(__file__)
        cls.repo_root = os.path.abspath(os.path.join(base_dir, "..", "..", ".."))
        cls.roles_dir = os.path.join(cls.repo_root, "roles")

    def test_every_compose_role_with_application_id_has_local_network(self):
        missing = []

        for role_path in sorted(glob.glob(os.path.join(self.roles_dir, "*"))):  # noqa: project-walk
            if not os.path.isdir(role_path):
                continue

            role_name = os.path.basename(role_path)
            compose_template = os.path.join(role_path, "templates", "compose.yml.j2")
            if not os.path.isfile(compose_template):
                continue

            vars_file = os.path.join(role_path, "vars", "main.yml")
            if not os.path.isfile(vars_file):
                continue

            vars_data = load_yaml_any(vars_file) or {}
            application_id = vars_data.get("application_id")
            if not application_id:
                continue

            server_file = os.path.join(role_path, "meta", "server.yml")
            subnet = None
            if os.path.isfile(server_file):
                server_data = load_yaml_any(server_file) or {}
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
