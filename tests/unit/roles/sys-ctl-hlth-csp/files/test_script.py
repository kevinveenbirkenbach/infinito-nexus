from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# add role files directory to PYTHONPATH
ROLE_FILES = Path(__file__).resolve().parents[5] / "roles/sys-ctl-hlth-csp/files"
sys.path.insert(0, str(ROLE_FILES))

import script  # noqa: E402


class TestExtractDomains(unittest.TestCase):
    @patch("script.os.listdir")
    def test_extract_domains_filters_valid_conf_domains(
        self, mock_listdir: MagicMock
    ) -> None:
        mock_listdir.return_value = [
            "example.com.conf",
            "api.example.com.conf",
            "not-a-domain.txt",
            "no-tld.conf",
            ".hidden.conf",
            "a..b.com.conf",
            "example.com.conf.bak",
            "localhost.conf",
            "sub.domain.co.uk.conf",
        ]

        domains = script.extract_domains("/etc/nginx/conf.d/http/servers/")
        self.assertIsInstance(domains, list)

        # valid: must match ^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\.conf$
        self.assertIn("example.com", domains)
        self.assertIn("api.example.com", domains)
        self.assertIn("sub.domain.co.uk", domains)

        # invalid ones
        self.assertNotIn("not-a-domain", domains)
        self.assertNotIn("no-tld", domains)
        self.assertNotIn(".hidden", domains)
        self.assertNotIn("a..b.com", domains)
        self.assertNotIn("example.com.conf", domains)
        self.assertNotIn("localhost", domains)

    @patch("script.os.listdir", side_effect=FileNotFoundError)
    def test_extract_domains_returns_none_when_directory_missing(
        self, _mock_listdir: MagicMock
    ) -> None:
        domains = script.extract_domains("/missing")
        self.assertIsNone(domains)


class TestBuildDockerCmd(unittest.TestCase):
    def test_build_docker_cmd_defaults_to_host_network(self) -> None:
        cmd = script.build_docker_cmd(
            image="ghcr.io/kevinveenbirkenbach/csp-checker:stable",
            domains=["example.com"],
            short_mode=False,
            ignore_network_blocks_from=[],
        )

        self.assertEqual(cmd[0:3], ["docker", "run", "--rm"])
        self.assertIn("--network", cmd)
        self.assertIn("host", cmd)
        self.assertIn("ghcr.io/kevinveenbirkenbach/csp-checker:stable", cmd)
        self.assertTrue(cmd[-1] == "example.com")

    def test_build_docker_cmd_can_disable_host_network(self) -> None:
        cmd = script.build_docker_cmd(
            image="img:tag",
            domains=["example.com"],
            short_mode=False,
            ignore_network_blocks_from=[],
            use_host_network=False,
        )

        self.assertEqual(cmd[0:3], ["docker", "run", "--rm"])
        self.assertNotIn("--network", cmd)
        self.assertNotIn("host", cmd)

    def test_build_docker_cmd_short_mode(self) -> None:
        cmd = script.build_docker_cmd(
            image="img:tag",
            domains=["example.com"],
            short_mode=True,
            ignore_network_blocks_from=[],
        )
        self.assertIn("--short", cmd)

    def test_build_docker_cmd_ignore_list_adds_separator_and_domains(self) -> None:
        cmd = script.build_docker_cmd(
            image="img:tag",
            domains=["a.example", "b.example"],
            short_mode=False,
            ignore_network_blocks_from=["pxscdn.com", "cdn.example.org"],
        )

        self.assertIn("--ignore-network-blocks-from", cmd)
        idx = cmd.index("--ignore-network-blocks-from")

        self.assertEqual(cmd[idx + 1], "pxscdn.com")
        self.assertEqual(cmd[idx + 2], "cdn.example.org")
        self.assertEqual(cmd[idx + 3], "--")
        self.assertEqual(cmd[idx + 4 :], ["a.example", "b.example"])


class TestRunChecker(unittest.TestCase):
    @patch("script.subprocess.run")
    def test_run_checker_pulls_image_when_always_pull_true(
        self, mock_run: MagicMock
    ) -> None:
        mock_run.side_effect = [
            MagicMock(returncode=0),  # pull
            MagicMock(returncode=3),  # run
        ]

        rc = script.run_checker(
            image="img:tag",
            domains=["example.com"],
            short_mode=True,
            ignore_network_blocks_from=[],
            always_pull=True,
            use_host_network=True,
        )

        self.assertEqual(rc, 3)
        self.assertGreaterEqual(mock_run.call_count, 2)

        pull_call = mock_run.call_args_list[0]
        self.assertEqual(pull_call.kwargs.get("check"), False)
        self.assertEqual(pull_call.args[0], ["docker", "pull", "img:tag"])

        run_call = mock_run.call_args_list[1]
        self.assertEqual(run_call.kwargs.get("check"), False)
        self.assertTrue(run_call.args[0][0:3] == ["docker", "run", "--rm"])

    @patch("script.subprocess.run")
    def test_run_checker_returns_127_if_docker_missing(
        self, mock_run: MagicMock
    ) -> None:
        mock_run.side_effect = FileNotFoundError

        rc = script.run_checker(
            image="img:tag",
            domains=["example.com"],
            short_mode=False,
            ignore_network_blocks_from=[],
            always_pull=False,
            use_host_network=True,
        )
        self.assertEqual(rc, 127)

    @patch("script.subprocess.run")
    def test_run_checker_returns_1_on_unexpected_exception(
        self, mock_run: MagicMock
    ) -> None:
        mock_run.side_effect = RuntimeError("boom")

        rc = script.run_checker(
            image="img:tag",
            domains=["example.com"],
            short_mode=False,
            ignore_network_blocks_from=[],
            always_pull=False,
            use_host_network=True,
        )
        self.assertEqual(rc, 1)


class TestMain(unittest.TestCase):
    @patch("script.run_checker")
    @patch("script.extract_domains")
    def test_main_exits_1_when_extract_domains_returns_none(
        self,
        mock_extract: MagicMock,
        mock_run_checker: MagicMock,
    ) -> None:
        mock_extract.return_value = None

        with patch.object(
            script.sys,
            "argv",
            ["script.py", "--nginx-config-dir", "/missing", "--image", "img:tag"],
        ):
            with self.assertRaises(SystemExit) as cm:
                script.main()

        self.assertEqual(cm.exception.code, 1)
        mock_run_checker.assert_not_called()

    @patch("script.run_checker")
    @patch("script.extract_domains")
    def test_main_exits_0_when_no_domains_found(
        self,
        mock_extract: MagicMock,
        mock_run_checker: MagicMock,
    ) -> None:
        mock_extract.return_value = []

        with patch.object(
            script.sys,
            "argv",
            ["script.py", "--nginx-config-dir", "/etc/nginx", "--image", "img:tag"],
        ):
            with self.assertRaises(SystemExit) as cm:
                script.main()

        self.assertEqual(cm.exception.code, 0)
        mock_run_checker.assert_not_called()

    @patch("script.run_checker")
    @patch("script.extract_domains")
    def test_main_passes_defaults_and_exits_with_run_checker_rc(
        self,
        mock_extract: MagicMock,
        mock_run_checker: MagicMock,
    ) -> None:
        mock_extract.return_value = ["example.com", "api.example.com"]
        mock_run_checker.return_value = 5

        with patch.object(
            script.sys,
            "argv",
            [
                "script.py",
                "--nginx-config-dir",
                "/etc/nginx",
                "--image",
                "img:tag",
                "--short",
                "--ignore-network-blocks-from",
                "pxscdn.com",
                "cdn.example.org",
            ],
        ):
            with self.assertRaises(SystemExit) as cm:
                script.main()

        self.assertEqual(cm.exception.code, 5)

        mock_run_checker.assert_called_once()
        kwargs = mock_run_checker.call_args.kwargs
        self.assertEqual(kwargs["image"], "img:tag")
        self.assertEqual(kwargs["domains"], ["example.com", "api.example.com"])
        self.assertTrue(kwargs["short_mode"])
        self.assertEqual(
            kwargs["ignore_network_blocks_from"], ["pxscdn.com", "cdn.example.org"]
        )
        self.assertFalse(kwargs["always_pull"])
        self.assertTrue(kwargs["use_host_network"])

    @patch("script.run_checker")
    @patch("script.extract_domains")
    def test_main_no_host_network_flag_disables_host_network(
        self,
        mock_extract: MagicMock,
        mock_run_checker: MagicMock,
    ) -> None:
        mock_extract.return_value = ["example.com"]
        mock_run_checker.return_value = 0

        with patch.object(
            script.sys,
            "argv",
            [
                "script.py",
                "--nginx-config-dir",
                "/etc/nginx",
                "--image",
                "img:tag",
                "--no-host-network",
            ],
        ):
            with self.assertRaises(SystemExit) as cm:
                script.main()

        self.assertEqual(cm.exception.code, 0)

        kwargs = mock_run_checker.call_args.kwargs
        self.assertFalse(kwargs["use_host_network"])


if __name__ == "__main__":
    unittest.main()
