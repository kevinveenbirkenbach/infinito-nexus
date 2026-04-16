from __future__ import annotations

import argparse
import os
import unittest
import unittest.mock

from cli.deploy.development import exec as exec_cmd


class TestDevelopmentExec(unittest.TestCase):
    def test_handler_forwards_services_disabled(self):
        compose = unittest.mock.Mock()
        compose.exec.return_value.returncode = 0

        args = argparse.Namespace(distro="debian", cmd=["--", "sh", "-lc", "true"])

        with unittest.mock.patch(
            "cli.deploy.development.exec.make_compose",
            return_value=compose,
        ):
            with unittest.mock.patch.dict(
                os.environ, {"SERVICES_DISABLED": "email"}, clear=False
            ):
                rc = exec_cmd.handler(args)

        self.assertEqual(rc, 0)
        compose.exec.assert_called_once_with(
            ["sh", "-lc", "true"],
            check=False,
            extra_env={"SERVICES_DISABLED": "email"},
        )

    def test_handler_omits_extra_env_when_services_disabled_unset(self):
        compose = unittest.mock.Mock()
        compose.exec.return_value.returncode = 0

        args = argparse.Namespace(distro="debian", cmd=["echo", "hi"])

        env = {k: v for k, v in os.environ.items() if k != "SERVICES_DISABLED"}
        with unittest.mock.patch(
            "cli.deploy.development.exec.make_compose",
            return_value=compose,
        ):
            with unittest.mock.patch.dict(os.environ, env, clear=True):
                rc = exec_cmd.handler(args)

        self.assertEqual(rc, 0)
        compose.exec.assert_called_once_with(
            ["echo", "hi"], check=False, extra_env=None
        )

    def test_handler_requires_command(self):
        args = argparse.Namespace(distro="debian", cmd=[])
        with self.assertRaises(SystemExit):
            exec_cmd.handler(args)


if __name__ == "__main__":
    unittest.main()
