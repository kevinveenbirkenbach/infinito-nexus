import glob
import os
import unittest

import yaml


class TestComposeRolesHaveLocalNetwork(unittest.TestCase):
    """Every role that defines an ``application_id`` in ``vars/main.yml`` and ships
    a Compose template (``templates/compose.yml.j2``) MUST have a dedicated network
    entry under ``defaults_networks.local`` in ``group_vars/all/08_networks.yml``.
    """

    @classmethod
    def setUpClass(cls):
        base_dir = os.path.dirname(__file__)
        cls.repo_root = os.path.abspath(os.path.join(base_dir, "..", "..", ".."))
        cls.networks_file = os.path.join(
            cls.repo_root, "group_vars", "all", "08_networks.yml"
        )
        cls.roles_dir = os.path.join(cls.repo_root, "roles")

        if not os.path.isfile(cls.networks_file):
            raise unittest.SkipTest(f"{cls.networks_file} does not exist.")

        with open(cls.networks_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        local = data.get("defaults_networks", {}).get("local", {}) or {}
        cls.local_network_names = set(local.keys())

    def test_every_compose_role_with_application_id_has_local_network(self):
        missing = []

        for role_path in sorted(glob.glob(os.path.join(self.roles_dir, "*"))):
            if not os.path.isdir(role_path):
                continue

            role_name = os.path.basename(role_path)
            compose_template = os.path.join(role_path, "templates", "compose.yml.j2")
            if not os.path.isfile(compose_template):
                continue

            vars_file = os.path.join(role_path, "vars", "main.yml")
            if not os.path.isfile(vars_file):
                continue

            with open(vars_file, "r", encoding="utf-8") as f:
                vars_data = yaml.safe_load(f) or {}
            application_id = vars_data.get("application_id")
            if not application_id:
                continue

            if application_id not in self.local_network_names:
                missing.append((role_name, application_id))

        if missing:
            details = "\n".join(
                f"  - role '{role}' (application_id='{app_id}')"
                for role, app_id in missing
            )
            self.fail(
                "The following roles ship a templates/compose.yml.j2 and define an "
                "application_id but have no entry under defaults_networks.local in "
                "group_vars/all/08_networks.yml:\n" + details
            )


if __name__ == "__main__":
    unittest.main()
