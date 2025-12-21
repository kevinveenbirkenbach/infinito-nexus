from __future__ import annotations

import subprocess
import unittest
from typing import Any, Dict, List, Tuple

from cli.deploy.dedicated import runner


class TestRunAnsiblePlaybook(unittest.TestCase):
    def _fake_run_side_effect(
        self,
        calls_store: List[Tuple[List[str], Dict[str, Any]]],
        ansible_rc: int = 0,
    ):
        """
        Side effect for subprocess.run that:
        - records all commands + kwargs to calls_store
        - returns a CompletedProcess with ansible_rc for ansible-playbook
        - returns success (rc=0) for all other commands
        """

        def _side_effect(cmd, *args, **kwargs):
            # Normalize command to list[str] for easier assertions
            if isinstance(cmd, list):
                norm_cmd = cmd
            else:
                norm_cmd = [cmd]

            calls_store.append((norm_cmd, dict(kwargs)))

            if norm_cmd and norm_cmd[0] == "ansible-playbook":
                return subprocess.CompletedProcess(
                    norm_cmd,
                    ansible_rc,
                    stdout="ANSIBLE_STDOUT\n",
                    stderr="ANSIBLE_STDERR\n",
                )

            return subprocess.CompletedProcess(norm_cmd, 0, stdout="", stderr="")

        return _side_effect

    @unittest.mock.patch("subprocess.run")
    def test_run_ansible_playbook_builds_correct_command_and_uses_repo_root_cwd(
        self, mock_run
    ):
        calls: List[Tuple[List[str], Dict[str, Any]]] = []
        mock_run.side_effect = self._fake_run_side_effect(calls, ansible_rc=0)

        repo_root = "/repo"
        playbook_path = "/repo/playbook.yml"
        inventory_validator_path = "/repo/cli/validate/inventory/__main__.py"

        modes: Dict[str, Any] = {
            "MODE_CLEANUP": True,
            "MODE_ASSERT": True,
            "MODE_DEBUG": True,
        }

        inventory_path = "/etc/inventories/github-ci/servers.yml"
        limit = "localhost"
        allowed_apps = ["web-app-foo", "web-app-bar"]
        password_file = "/etc/inventories/github-ci/.password"

        runner.run_ansible_playbook(
            repo_root=repo_root,
            cli_root="/repo/cli",  # currently unused, but kept in signature
            playbook_path=playbook_path,
            inventory_validator_path=inventory_validator_path,
            inventory=inventory_path,
            modes=modes,
            limit=limit,
            allowed_applications=allowed_apps,
            password_file=password_file,
            verbose=1,
            skip_build=False,
            logs=False,
            diff=True,
        )

        def was_called(cmd: List[str]) -> bool:
            return any(call_cmd == cmd for call_cmd, _kw in calls)

        # Cleanup, build, tests (make must run in repo_root)
        self.assertTrue(was_called(["make", "clean"]), "Expected 'make clean'")
        self.assertTrue(was_called(["make", "setup"]), "Expected 'make setup'")

        for call_cmd, kw in calls:
            if call_cmd and call_cmd[0] == "make":
                self.assertEqual(
                    kw.get("cwd"),
                    repo_root,
                    f"Expected make call to use cwd={repo_root}, got {kw.get('cwd')}",
                )

        # Inventory validation call must use sys.executable + validator path and cwd=repo_root
        inv_calls = [
            (call_cmd, kw)
            for call_cmd, kw in calls
            if isinstance(call_cmd, list)
            and any("inventory/__main__.py" in part for part in call_cmd)
        ]
        self.assertTrue(
            inv_calls,
            "Expected inventory validation call (... inventory/__main__.py ...)",
        )
        for call_cmd, kw in inv_calls:
            self.assertEqual(kw.get("cwd"), repo_root)

        # The last call should be ansible-playbook
        self.assertGreaterEqual(len(calls), 1)
        last_cmd, last_kw = calls[-1]
        self.assertEqual(last_cmd[0], "ansible-playbook")
        self.assertEqual(last_kw.get("cwd"), repo_root)

        # Inventory and playbook ordering: -i <inventory> <playbook>
        self.assertIn("-i", last_cmd)
        self.assertIn(inventory_path, last_cmd)
        idx_inv = last_cmd.index(inventory_path)
        self.assertGreater(len(last_cmd), idx_inv + 1)
        self.assertEqual(last_cmd[idx_inv + 1], playbook_path)

        # Limit handling
        self.assertIn("-l", last_cmd)
        self.assertIn(limit, last_cmd)

        # Allowed applications extra var
        last_cmd_str = " ".join(last_cmd)
        self.assertIn("allowed_applications=web-app-foo,web-app-bar", last_cmd_str)

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
        self.assertNotIn("text", last_kw)
        self.assertNotIn("capture_output", last_kw)

    @unittest.mock.patch("subprocess.run")
    def test_run_ansible_playbook_failure_exits_with_code_and_skips_phases(
        self, mock_run
    ):
        calls: List[Tuple[List[str], Dict[str, Any]]] = []
        mock_run.side_effect = self._fake_run_side_effect(calls, ansible_rc=4)

        repo_root = "/repo"
        playbook_path = "/repo/playbook.yml"
        inventory_validator_path = "/repo/cli/validate/inventory/__main__.py"

        modes: Dict[str, Any] = {
            "MODE_CLEANUP": False,
            "MODE_ASSERT": False,
            "MODE_DEBUG": False,
        }

        with self.assertRaises(SystemExit) as ctx:
            runner.run_ansible_playbook(
                repo_root=repo_root,
                cli_root="/repo/cli",
                playbook_path=playbook_path,
                inventory_validator_path=inventory_validator_path,
                inventory="/etc/inventories/github-ci/servers.yml",
                modes=modes,
                limit=None,
                allowed_applications=None,
                password_file=None,
                verbose=0,
                skip_build=True,
                logs=False,
                diff=False,
            )

        self.assertEqual(ctx.exception.code, 4)

        # Ensure ansible-playbook was invoked once
        self.assertTrue(
            any(
                call_cmd and call_cmd[0] == "ansible-playbook"
                for call_cmd, _kw in calls
            ),
            "ansible-playbook should have been invoked once in the error path",
        )

        # No cleanup, no build, no tests, no inventory validation
        self.assertFalse(any(call_cmd == ["make", "clean"] for call_cmd, _kw in calls))
        self.assertFalse(any(call_cmd == ["make", "setup"] for call_cmd, _kw in calls))
        self.assertFalse(
            any(call_cmd == ["make", "test-messy"] for call_cmd, _kw in calls)
        )
        self.assertFalse(
            any(
                any("inventory/__main__.py" in part for part in call_cmd)
                for call_cmd, _kw in calls
            ),
            "Inventory validation should be skipped when MODE_ASSERT is False",
        )

    @unittest.mock.patch("subprocess.run")
    def test_run_ansible_playbook_cleanup_with_logs_uses_clean(self, mock_run):
        calls: List[Tuple[List[str], Dict[str, Any]]] = []
        mock_run.side_effect = self._fake_run_side_effect(calls, ansible_rc=0)

        repo_root = "/repo"
        playbook_path = "/repo/playbook.yml"
        inventory_validator_path = "/repo/cli/validate/inventory/__main__.py"

        modes: Dict[str, Any] = {
            "MODE_CLEANUP": True,
            "MODE_ASSERT": False,
            "MODE_DEBUG": False,
        }

        runner.run_ansible_playbook(
            repo_root=repo_root,
            cli_root="/repo/cli",
            playbook_path=playbook_path,
            inventory_validator_path=inventory_validator_path,
            inventory="/etc/inventories/github-ci/servers.yml",
            modes=modes,
            limit=None,
            allowed_applications=None,
            password_file=None,
            verbose=0,
            skip_build=True,
            logs=True,
            diff=False,
        )

        self.assertTrue(
            any(call_cmd == ["make", "clean"] for call_cmd, _kw in calls),
            "Expected 'make clean' when MODE_CLEANUP=true (logs flag ignored by Makefile)",
        )


if __name__ == "__main__":
    unittest.main()
