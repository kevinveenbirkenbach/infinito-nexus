import os
import yaml
import unittest


class TestAnsibleRolesMetadata(unittest.TestCase):
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ROLES_DIR = os.path.join(ROOT_DIR, "roles")

    @classmethod
    def setUpClass(cls):
        all_dirs = os.listdir(cls.ROLES_DIR)
        cls.roles = [
            d
            for d in all_dirs
            if (os.path.isdir(os.path.join(cls.ROLES_DIR, d)) and d != "__pycache__")
        ]

    def test_each_role_has_valid_meta(self):
        """
        Ensure each Ansible role has a valid meta/main.yml
        with the fields that Sphinx generators expect.
        """
        for role in self.roles:
            with self.subTest(role=role):
                role_path = os.path.join(self.ROLES_DIR, role)
                meta_file = os.path.join(role_path, "meta", "main.yml")
                self.assertTrue(
                    os.path.exists(meta_file),
                    msg=f"Missing meta/main.yml in role '{role}'",
                )

                with open(meta_file, "r", encoding="utf-8") as f:
                    raw = f.read()
                    meta_data = yaml.safe_load(raw) or {}

                # meta_data must be a dict
                self.assertIsInstance(
                    meta_data, dict, msg=f"Meta data for role '{role}' is not a dict"
                )

                # description inside galaxy_info
                galaxy_info = meta_data.get("galaxy_info") or {}
                self.assertIsInstance(
                    galaxy_info,
                    dict,
                    msg=f"'galaxy_info' missing or not a dict in meta for role '{role}'",
                )

                self.assertIn(
                    "description",
                    galaxy_info,
                    msg=f"'description' missing in galaxy_info for role '{role}'",
                )
                self.assertTrue(
                    galaxy_info["description"],
                    msg=f"'description' is empty in galaxy_info for role '{role}'",
                )

                # no empty keys or None values in galaxy_info
                for key, value in galaxy_info.items():
                    self.assertTrue(key, msg=f"Empty galaxy_info key in role '{role}'")
                    self.assertIsNotNone(
                        value,
                        msg=f"None value for galaxy_info['{key}'] in role '{role}'",
                    )


if __name__ == "__main__":
    unittest.main()
