import os
import tempfile
import unittest
from typing import Any, Dict, List
from unittest import mock
import subprocess

from cli.deploy import dedicated as deploy


class TestParseBoolLiteral(unittest.TestCase):
    def test_true_values(self):
        self.assertTrue(deploy._parse_bool_literal("true"))
        self.assertTrue(deploy._parse_bool_literal("True"))
        self.assertTrue(deploy._parse_bool_literal(" yes "))
        self.assertTrue(deploy._parse_bool_literal("ON"))

    def test_false_values(self):
        self.assertFalse(deploy._parse_bool_literal("false"))
        self.assertFalse(deploy._parse_bool_literal("False"))
        self.assertFalse(deploy._parse_bool_literal(" no "))
        self.assertFalse(deploy._parse_bool_literal("off"))

    def test_unknown_value(self):
        self.assertIsNone(deploy._parse_bool_literal("maybe"))
        self.assertIsNone(deploy._parse_bool_literal(""))
        self.assertIsNone(deploy._parse_bool_literal("  "))


class TestLoadModesFromYaml(unittest.TestCase):
    def test_load_modes_basic(self):
        content = """\
MODE_CLEANUP: true   # cleanup before deploy
MODE_DEBUG: false    # debug output
MODE_ASSERT: null    # inventory assertion
OTHER_KEY: true      # should be ignored (no MODE_ prefix)
"""

        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as f:
            path = f.name
            f.write(content)
            f.flush()

        try:
            modes = deploy.load_modes_from_yaml(path)
        finally:
            os.unlink(path)

        self.assertEqual(len(modes), 3)

        by_name = {m["name"]: m for m in modes}

        self.assertIn("MODE_CLEANUP", by_name)
        self.assertIn("MODE_DEBUG", by_name)
        self.assertIn("MODE_ASSERT", by_name)

        self.assertEqual(by_name["MODE_CLEANUP"]["default"], True)
        self.assertEqual(by_name["MODE_DEBUG"]["default"], False)
        self.assertIsNone(by_name["MODE_ASSERT"]["default"])
        self.assertEqual(by_name["MODE_CLEANUP"]["help"], "cleanup before deploy")

    def test_load_modes_ignores_non_mode_keys(self):
        content = """\
FOO: true
BAR: false
MODE_FOO: true
"""

        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as f:
            path = f.name
            f.write(content)
            f.flush()

        try:
            modes = deploy.load_modes_from_yaml(path)
        finally:
            os.unlink(path)

        self.assertEqual(len(modes), 1)
        self.assertEqual(modes[0]["name"], "MODE_FOO")


class TestDynamicModes(unittest.TestCase):
    def setUp(self):
        self.modes_meta = [
            {"name": "MODE_CLEANUP", "default": True, "help": "Cleanup before run"},
            {"name": "MODE_DEBUG", "default": False, "help": "Debug output"},
            {"name": "MODE_ASSERT", "default": None, "help": "Inventory assertion"},
        ]

    def test_add_dynamic_mode_args_and_build_modes_defaults(self):
        from argparse import ArgumentParser

        real_parser = ArgumentParser()
        spec = deploy.add_dynamic_mode_args(real_parser, self.modes_meta)

        self.assertIn("MODE_CLEANUP", spec)
        self.assertIn("MODE_DEBUG", spec)
        self.assertIn("MODE_ASSERT", spec)

        # No flags passed → defaults apply
        args = real_parser.parse_args([])
        modes = deploy.build_modes_from_args(spec, args)

        self.assertTrue(modes["MODE_CLEANUP"])   # default True
        self.assertFalse(modes["MODE_DEBUG"])    # default False
        self.assertNotIn("MODE_ASSERT", modes)   # explicit, not set

    def test_add_dynamic_mode_args_and_build_modes_flags_true(self):
        from argparse import ArgumentParser

        parser = ArgumentParser()
        spec = deploy.add_dynamic_mode_args(parser, self.modes_meta)

        # MODE_CLEANUP: true   → --skip-cleanup  sets it to False
        # MODE_DEBUG:   false  → --debug        sets it to True
        # MODE_ASSERT:  None   → --assert true  sets it to True
        args = parser.parse_args(["--skip-cleanup", "--debug", "--assert", "true"])
        modes = deploy.build_modes_from_args(spec, args)

        self.assertFalse(modes["MODE_CLEANUP"])
        self.assertTrue(modes["MODE_DEBUG"])
        self.assertTrue(modes["MODE_ASSERT"])

    def test_add_dynamic_mode_args_and_build_modes_flags_false_explicit(self):
        from argparse import ArgumentParser

        parser = ArgumentParser()
        spec = deploy.add_dynamic_mode_args(parser, self.modes_meta)

        # explicit false for MODE_ASSERT
        args = parser.parse_args(["--assert", "false"])
        modes = deploy.build_modes_from_args(spec, args)

        self.assertTrue(modes["MODE_CLEANUP"])   # still default True
        self.assertFalse(modes["MODE_DEBUG"])    # still default False
        self.assertIn("MODE_ASSERT", modes)
        self.assertFalse(modes["MODE_ASSERT"])


class TestValidateApplicationIds(unittest.TestCase):
    def test_no_ids_does_nothing(self):
        # Should not raise
        deploy.validate_application_ids("inventories/github-ci/servers.yml", [])

    @mock.patch("module_utils.valid_deploy_id.ValidDeployId")
    def test_invalid_ids_raise_system_exit(self, mock_vdi_cls):
        instance = mock_vdi_cls.return_value
        instance.validate.return_value = {
            "web-app-foo": {"allowed": False, "in_inventory": True},
            "web-app-bar": {"allowed": True, "in_inventory": False},
        }

        with self.assertRaises(SystemExit) as ctx:
            deploy.validate_application_ids(
                "inventories/github-ci/servers.yml",
                ["web-app-foo", "web-app-bar"],
            )

        self.assertEqual(ctx.exception.code, 1)
        instance.validate.assert_called_once_with(
            "inventories/github-ci/servers.yml",
            ["web-app-foo", "web-app-bar"],
        )


class TestRunAnsiblePlaybook(unittest.TestCase):
    def _fake_run_side_effect(
        self,
        calls_store: List[List[str]],
        ansible_rc: int = 0,
    ):
        """
        Side effect for subprocess.run that:
        - records all commands to calls_store
        - returns a CompletedProcess with ansible_rc for ansible-playbook
        - returns success (rc=0) for all other commands
        """

        def _side_effect(cmd, *args, **kwargs):
            if isinstance(cmd, list):
                calls_store.append(cmd)
            else:
                calls_store.append([cmd])

            if isinstance(cmd, list) and cmd and cmd[0] == "ansible-playbook":
                return subprocess.CompletedProcess(
                    cmd,
                    ansible_rc,
                    stdout="ANSIBLE_STDOUT\n",
                    stderr="ANSIBLE_STDERR\n",
                )

            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        return _side_effect

    @mock.patch("subprocess.run")
    def test_run_ansible_playbook_builds_correct_command(self, mock_run):
        calls: List[List[str]] = []
        mock_run.side_effect = self._fake_run_side_effect(calls, ansible_rc=0)

        modes: Dict[str, Any] = {
            "MODE_CLEANUP": True,
            "MODE_ASSERT": True,
            "MODE_DEBUG": True,
        }

        inventory_path = "inventories/github-ci/servers.yml"
        limit = "localhost"
        allowed_apps = ["web-app-foo", "web-app-bar"]
        password_file = "inventories/github-ci/.password"

        deploy.run_ansible_playbook(
            inventory=inventory_path,
            modes=modes,
            limit=limit,
            allowed_applications=allowed_apps,
            password_file=password_file,
            verbose=1,
            skip_build=False,
            skip_tests=False,
            logs=False,
            diff=True,
        )

        # Cleanup, build, tests
        self.assertTrue(
            any(call == ["make", "clean"] for call in calls),
            "Expected 'make clean' when MODE_CLEANUP is true",
        )
        self.assertTrue(
            any(call == ["make", "setup"] for call in calls),
            "Expected 'make setup' when skip_build=False",
        )
        self.assertTrue(
            any(call == ["make", "test-messy"] for call in calls),
            "Expected 'make test-messy' when skip_tests=False",
        )
        self.assertTrue(
            any(
                isinstance(call, list)
                and any("inventory.py" in part for part in call)
                for call in calls
            ),
            "Expected inventory validation call (... inventory.py ...)",
        )

        # The last call should be ansible-playbook
        self.assertGreaterEqual(len(calls), 1)
        last_cmd = calls[-1]
        self.assertEqual(last_cmd[0], "ansible-playbook")

        # Inventory and playbook ordering: -i <inventory> <playbook>
        self.assertIn("-i", last_cmd)
        self.assertIn(inventory_path, last_cmd)

        idx_inv = last_cmd.index(inventory_path)
        self.assertGreater(len(last_cmd), idx_inv + 1)
        playbook_arg = last_cmd[idx_inv + 1]
        self.assertTrue(
            playbook_arg.endswith("playbook.yml"),
            f"playbook argument should end with 'playbook.yml', got: {playbook_arg}",
        )

        # Limit handling
        self.assertIn("-l", last_cmd)
        self.assertIn(limit, last_cmd)

        # Allowed applications extra var
        last_cmd_str = " ".join(last_cmd)
        self.assertIn(
            "allowed_applications=web-app-foo,web-app-bar",
            last_cmd_str,
        )

        # MODE_* variables
        self.assertIn("MODE_CLEANUP=true", last_cmd_str)
        self.assertIn("MODE_ASSERT=true", last_cmd_str)
        self.assertIn("MODE_DEBUG=true", last_cmd_str)

        # Vault password file
        self.assertIn("--vault-password-file", last_cmd)
        self.assertIn(password_file, last_cmd)

        # Diff flag
        self.assertIn("--diff", last_cmd)

        # Verbosity should be at least -vvv when MODE_DEBUG=True
        self.assertTrue(
            any(arg.startswith("-vvv") for arg in last_cmd),
            "Expected at least -vvv because MODE_DEBUG=True",
        )

        # Ensure we did not accidentally set text/capture_output in the final run
        last_call = mock_run.call_args_list[-1]
        self.assertNotIn("text", last_call.kwargs)
        self.assertNotIn("capture_output", last_call.kwargs)

    @mock.patch("subprocess.run")
    def test_run_ansible_playbook_failure_exits_with_code_and_skips_phases(self, mock_run):
        calls: List[List[str]] = []
        mock_run.side_effect = self._fake_run_side_effect(calls, ansible_rc=4)

        modes: Dict[str, Any] = {
            "MODE_CLEANUP": False,
            "MODE_ASSERT": False,
            "MODE_DEBUG": False,
        }

        with self.assertRaises(SystemExit) as ctx:
            deploy.run_ansible_playbook(
                inventory="inventories/github-ci/servers.yml",
                modes=modes,
                limit=None,
                allowed_applications=None,
                password_file=None,
                verbose=0,
                skip_build=True,
                skip_tests=True,
                logs=False,
                diff=False,
            )

        self.assertEqual(ctx.exception.code, 4)
        self.assertTrue(
            any(call and call[0] == "ansible-playbook" for call in calls),
            "ansible-playbook should have been invoked once in the error path",
        )
        # No cleanup, no build, no tests, no inventory validation
        self.assertFalse(any(call == ["make", "clean"] for call in calls))
        self.assertFalse(any(call == ["make", "setup"] for call in calls))
        self.assertFalse(any(call == ["make", "test-messy"] for call in calls))
        self.assertFalse(
            any(
                isinstance(call, list)
                and any("inventory.py" in part for part in call)
                for call in calls
            )
        )

    @mock.patch("subprocess.run")
    def test_run_ansible_playbook_cleanup_with_logs_uses_clean_keep_logs(self, mock_run):
        calls: List[List[str]] = []
        mock_run.side_effect = self._fake_run_side_effect(calls, ansible_rc=0)

        modes: Dict[str, Any] = {
            "MODE_CLEANUP": True,
            "MODE_ASSERT": False,
            "MODE_DEBUG": False,
        }

        deploy.run_ansible_playbook(
            inventory="inventories/github-ci/servers.yml",
            modes=modes,
            limit=None,
            allowed_applications=None,
            password_file=None,
            verbose=0,
            skip_build=True,
            skip_tests=True,
            logs=True,
            diff=False,
        )

        self.assertTrue(
            any(call == ["make", "clean-keep-logs"] for call in calls),
            "Expected 'make clean-keep-logs' when MODE_CLEANUP=true and logs=True",
        )


if __name__ == "__main__":
    unittest.main()
