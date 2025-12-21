import os
import unittest

ROLES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../roles")
)


class TestRolesHaveMetaMain(unittest.TestCase):
    def test_each_role_has_meta_main(self):
        missing_meta = []

        for role in os.listdir(ROLES_DIR):
            # Ignore Python cache and hidden directories
            if role.startswith(".") or role == "__pycache__":
                continue

            role_path = os.path.join(ROLES_DIR, role)
            if not os.path.isdir(role_path):
                continue

            meta_main = os.path.join(role_path, "meta", "main.yml")
            if not os.path.isfile(meta_main):
                missing_meta.append(role)

        if missing_meta:
            self.fail(
                "The following roles are missing meta/main.yml:\n"
                + "\n".join(missing_meta)
            )


if __name__ == "__main__":
    unittest.main()
