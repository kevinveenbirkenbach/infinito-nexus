import shutil
import tempfile
import unittest
from pathlib import Path

# Adjust this import to match the real path in your project
from cli.fix.vars_main_files import ROLES_DIR, run
from utils.cache.yaml import dump_yaml, load_yaml_any
from utils.roles.mapping import ROLE_FILE_VARS_MAIN


class TestEnsureVarsMain(unittest.TestCase):
    def setUp(self):
        # create a temporary directory to act as our roles dir
        self.tmpdir = tempfile.mkdtemp()
        self.roles_dir = str(Path(self.tmpdir) / "roles")
        Path(self.roles_dir).mkdir()

        # Monkey-patch the module's ROLES_DIR to point here
        self._orig_roles_dir = ROLES_DIR
        __import__(
            "cli.fix.vars_main_files", fromlist=["ROLES_DIR"]
        ).ROLES_DIR = self.roles_dir

    def tearDown(self):
        # restore and cleanup
        __import__(
            "cli.fix.vars_main_files", fromlist=["ROLES_DIR"]
        ).ROLES_DIR = self._orig_roles_dir
        shutil.rmtree(self.tmpdir)

    def _make_role(self, name, vars_content=None):
        """
        Create a role under self.roles_dir/name
        If vars_content is given, writes that to vars/main.yml
        """
        role_path = str(Path(self.roles_dir) / name)
        Path(str(Path(role_path) / "vars")).mkdir(parents=True)
        if vars_content is not None:
            dump_yaml(str(Path(role_path) / ROLE_FILE_VARS_MAIN), vars_content)
        return role_path

    def test_creates_missing_vars_main(self):
        # Create a role with no vars/main.yml
        role = self._make_role("desk-foobar")
        # Ensure no file exists yet
        self.assertFalse(Path(str(Path(role) / ROLE_FILE_VARS_MAIN)).exists())

        # Run with overwrite=False, preview=False
        run(prefix="desk-", preview=False, overwrite=False)

        # Now file must exist
        vm = str(Path(role) / ROLE_FILE_VARS_MAIN)
        self.assertTrue(Path(vm).exists())

        data = load_yaml_any(vm)
        # Expect application_id: 'foobar'
        self.assertEqual(data.get("application_id"), "foobar")

    def test_overwrite_updates_only_application_id(self):
        # Create a role with an existing vars/main.yml
        initial = {"application_id": "wrong", "foo": "bar"}
        role = self._make_role("desk-baz", vars_content=initial.copy())

        run(prefix="desk-", preview=False, overwrite=True)

        path = str(Path(role) / ROLE_FILE_VARS_MAIN)
        data = load_yaml_any(path)

        # application_id must be corrected...
        self.assertEqual(data.get("application_id"), "baz")
        # ...but other keys must survive
        self.assertIn("foo", data)
        self.assertEqual(data["foo"], "bar")

    def test_preview_mode_does_not_write(self):
        # Create a role directory but with no vars/main.yml
        role = self._make_role("desk-preview")
        vm = str(Path(role) / ROLE_FILE_VARS_MAIN)
        # Run in preview => no file creation
        run(prefix="desk-", preview=True, overwrite=False)
        self.assertFalse(Path(vm).exists())


if __name__ == "__main__":
    unittest.main()
