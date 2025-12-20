import os
import shutil
import tempfile
import unittest
import yaml

# Adjust this import to match the real path in your project
from cli.fix.vars_main_files import run, ROLES_DIR


class TestEnsureVarsMain(unittest.TestCase):
    def setUp(self):
        # create a temporary directory to act as our roles dir
        self.tmpdir = tempfile.mkdtemp()
        self.roles_dir = os.path.join(self.tmpdir, "roles")
        os.mkdir(self.roles_dir)

        # Monkey-patch the module's ROLES_DIR to point here
        self._orig_roles_dir = ROLES_DIR
        setattr(
            __import__("cli.fix.vars_main_files", fromlist=["ROLES_DIR"]),
            "ROLES_DIR",
            self.roles_dir,
        )

    def tearDown(self):
        # restore and cleanup
        setattr(
            __import__("cli.fix.vars_main_files", fromlist=["ROLES_DIR"]),
            "ROLES_DIR",
            self._orig_roles_dir,
        )
        shutil.rmtree(self.tmpdir)

    def _make_role(self, name, vars_content=None):
        """
        Create a role under self.roles_dir/name
        If vars_content is given, writes that to vars/main.yml
        """
        role_path = os.path.join(self.roles_dir, name)
        os.makedirs(os.path.join(role_path, "vars"))
        if vars_content is not None:
            with open(os.path.join(role_path, "vars", "main.yml"), "w") as f:
                yaml.safe_dump(vars_content, f)
        return role_path

    def test_creates_missing_vars_main(self):
        # Create a role with no vars/main.yml
        role = self._make_role("desk-foobar")
        # Ensure no file exists yet
        self.assertFalse(os.path.exists(os.path.join(role, "vars", "main.yml")))

        # Run with overwrite=False, preview=False
        run(prefix="desk-", preview=False, overwrite=False)

        # Now file must exist
        vm = os.path.join(role, "vars", "main.yml")
        self.assertTrue(os.path.exists(vm))

        with open(vm) as f:
            data = yaml.safe_load(f)
        # Expect application_id: 'foobar'
        self.assertEqual(data.get("application_id"), "foobar")

    def test_overwrite_updates_only_application_id(self):
        # Create a role with an existing vars/main.yml
        initial = {"application_id": "wrong", "foo": "bar"}
        role = self._make_role("desk-baz", vars_content=initial.copy())

        run(prefix="desk-", preview=False, overwrite=True)

        path = os.path.join(role, "vars", "main.yml")
        with open(path) as f:
            data = yaml.safe_load(f)

        # application_id must be corrected...
        self.assertEqual(data.get("application_id"), "baz")
        # ...but other keys must survive
        self.assertIn("foo", data)
        self.assertEqual(data["foo"], "bar")

    def test_preview_mode_does_not_write(self):
        # Create a role directory but with no vars/main.yml
        role = self._make_role("desk-preview")
        vm = os.path.join(role, "vars", "main.yml")
        # Run in preview => no file creation
        run(prefix="desk-", preview=True, overwrite=False)
        self.assertFalse(os.path.exists(vm))


if __name__ == "__main__":
    unittest.main()
