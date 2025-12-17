import os
import unittest
import tempfile
import shutil
import yaml
from pathlib import Path
import subprocess


class TestGenerateDefaultApplications(unittest.TestCase):
    def setUp(self):
        # Path to the generator script under test
        self.script_path = (
            Path(__file__).resolve().parents[4] / "cli" / "setup" / "applications.py"
        )
        # Create temp role structure
        self.temp_dir = Path(tempfile.mkdtemp())
        self.roles_dir = self.temp_dir / "roles"
        self.roles_dir.mkdir()

        # Sample role
        self.sample_role = self.roles_dir / "web-app-testapp"
        (self.sample_role / "vars").mkdir(parents=True)
        (self.sample_role / "config").mkdir(parents=True)

        # Write application_id and configuration
        (self.sample_role / "vars" / "main.yml").write_text("application_id: testapp\n")
        (self.sample_role / "config" / "main.yml").write_text("foo: bar\nbaz: 123\n")

        # Output file path
        self.output_file = self.temp_dir / "group_vars" / "all" / "04_applications.yml"

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_script_generates_expected_yaml(self):
        script_path = (
            Path(__file__).resolve().parent.parent.parent.parent.parent
            / "cli/setup/applications.py"
        )

        result = subprocess.run(
            [
                "python3",
                str(script_path),
                "--roles-dir",
                str(self.roles_dir),
                "--output-file",
                str(self.output_file),
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(self.output_file.exists(), "Output file was not created.")

        data = yaml.safe_load(self.output_file.read_text())
        self.assertIn("defaults_applications", data)
        self.assertIn("testapp", data["defaults_applications"])
        self.assertEqual(data["defaults_applications"]["testapp"]["foo"], "bar")
        self.assertEqual(data["defaults_applications"]["testapp"]["baz"], 123)

    def test_missing_config_adds_empty_defaults(self):
        """
        If a role has vars/main.yml but no config/main.yml,
        the generator should still create an entry with an empty dict.
        """
        # Create a role with vars/main.yml but without config/main.yml
        role_no_config = self.roles_dir / "role-no-config"
        (role_no_config / "vars").mkdir(parents=True)
        (role_no_config / "vars" / "main.yml").write_text(
            "application_id: noconfigapp\n"
        )

        # Run the generator
        result = subprocess.run(
            [
                "python3",
                str(self.script_path),
                "--roles-dir",
                str(self.roles_dir),
                "--output-file",
                str(self.output_file),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        # Verify the output YAML
        data = yaml.safe_load(self.output_file.read_text())
        apps = data.get("defaults_applications", {})

        # The new application_id must exist and be an empty dict
        self.assertIn("noconfigapp", apps)
        self.assertEqual(apps["noconfigapp"], {})

    def test_no_config_directory_adds_empty_defaults(self):
        """
        If a role has vars/main.yml but no config directory at all,
        the generator should still emit an empty-dict entry.
        """
        # Create a role with vars/main.yml but do not create config/ at all
        role_no_cfg_dir = self.roles_dir / "role-no-cfg-dir"
        (role_no_cfg_dir / "vars").mkdir(parents=True)
        (role_no_cfg_dir / "vars" / "main.yml").write_text(
            "application_id: nocfgdirapp\n"
        )
        # Note: no config/ directory is created here

        # Run the generator again
        result = subprocess.run(
            [
                "python3",
                str(self.script_path),
                "--roles-dir",
                str(self.roles_dir),
                "--output-file",
                str(self.output_file),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        # Load and inspect the output
        data = yaml.safe_load(self.output_file.read_text())
        apps = data.get("defaults_applications", {})

        # Ensure that the application_id appears with an empty mapping
        self.assertIn("nocfgdirapp", apps)
        self.assertEqual(apps["nocfgdirapp"], {})

    def test_applications_sorted_by_key(self):
        """
        Ensure that defaults_applications keys are written in alphabetical order.
        """
        # Create several roles in non-sorted order
        for name, cfg in [
            ("web-app-zeta", {"vars_id": "zeta", "cfg": "z: 1\n"}),
            ("web-app-alpha", {"vars_id": "alpha", "cfg": "a: 1\n"}),
            ("web-app-mu", {"vars_id": "mu", "cfg": "m: 1\n"}),
        ]:
            role = self.roles_dir / name
            (role / "vars").mkdir(parents=True, exist_ok=True)
            (role / "config").mkdir(parents=True, exist_ok=True)
            (role / "vars" / "main.yml").write_text(
                f"application_id: {cfg['vars_id']}\n"
            )
            (role / "config" / "main.yml").write_text(cfg["cfg"])

        # Run generator
        result = subprocess.run(
            [
                "python3",
                str(self.script_path),
                "--roles-dir",
                str(self.roles_dir),
                "--output-file",
                str(self.output_file),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        # Validate order of keys in YAML
        data = yaml.safe_load(self.output_file.read_text())
        apps = data.get("defaults_applications", {})
        # dict preserves insertion order in Python 3.7+, PyYAML keeps document order
        keys_in_file = list(apps.keys())

        self.assertEqual(
            keys_in_file,
            sorted(keys_in_file),
            msg=f"Applications are not sorted: {keys_in_file}",
        )
        # Sanity: all expected apps present
        for app in ("alpha", "mu", "zeta", "testapp"):
            self.assertIn(app, apps)

    def test_sorting_is_stable_across_runs(self):
        """
        Running the generator multiple times yields identical content (stable sort).
        """
        # Create a couple more roles (unsorted)
        for name, appid in [
            ("web-app-beta", "beta"),
            ("web-app-delta", "delta"),
        ]:
            role = self.roles_dir / name
            (role / "vars").mkdir(parents=True, exist_ok=True)
            (role / "config").mkdir(parents=True, exist_ok=True)
            (role / "vars" / "main.yml").write_text(f"application_id: {appid}\n")
            (role / "config" / "main.yml").write_text("key: value\n")

        # First run
        result1 = subprocess.run(
            [
                "python3",
                str(self.script_path),
                "--roles-dir",
                str(self.roles_dir),
                "--output-file",
                str(self.output_file),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result1.returncode, 0, msg=result1.stderr)
        content_run1 = self.output_file.read_text()

        # Second run (simulate potential filesystem order differences by touching dirs)
        for p in self.roles_dir.iterdir():
            os.utime(p, None)

        result2 = subprocess.run(
            [
                "python3",
                str(self.script_path),
                "--roles-dir",
                str(self.roles_dir),
                "--output-file",
                str(self.output_file),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result2.returncode, 0, msg=result2.stderr)
        content_run2 = self.output_file.read_text()

        self.assertEqual(
            content_run1,
            content_run2,
            msg="Output differs between runs; sorting should be stable.",
        )


if __name__ == "__main__":
    unittest.main()
