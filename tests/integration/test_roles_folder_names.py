#!/usr/bin/env python3

import os
import unittest


class TestRolesFolderNames(unittest.TestCase):
    def test_no_underscore_in_role_folder_names(self):
        """
        Integration test that verifies none of the folders under 'roles' contain an underscore in their name,
        ignoring the '__pycache__' folder.
        """
        # Determine the absolute path to the 'roles' directory
        roles_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "roles")
        )

        # List all entries in the roles directory
        try:
            entries = os.listdir(roles_dir)
        except FileNotFoundError:
            self.fail(f"Roles directory not found at expected location: {roles_dir}")

        # Identify any role folders containing underscores, excluding '__pycache__'
        invalid = []
        for name in entries:
            # Skip the '__pycache__' directory
            if name == "__pycache__":
                continue
            path = os.path.join(roles_dir, name)
            if os.path.isdir(path) and "_" in name:
                invalid.append(name)

        # Fail the test if any invalid folder names are found
        if invalid:
            self.fail(
                f"Role folder names must not contain underscores: {', '.join(sorted(invalid))}"
            )


if __name__ == "__main__":
    unittest.main()
