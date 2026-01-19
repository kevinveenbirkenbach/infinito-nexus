from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch


class TestSufficientStorageCLI(unittest.TestCase):
    def test_prints_space_separated_matching_roles(self) -> None:
        from cli.meta.applications.sufficient_storage import __main__ as cli_main

        fake_roles = ["web-app-a", "web-app-b"]

        with (
            patch.object(
                cli_main,
                "filter_roles_by_min_storage",
                return_value=fake_roles,
            ),
            patch.object(
                cli_main.sys,
                "argv",
                [
                    "prog",
                    "--roles",
                    "web-app-a",
                    "web-app-b",
                    "--required-storage",
                    "10G",
                ],
            ),
        ):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = cli_main.main()

        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue().strip(), "web-app-a web-app-b")

    def test_prints_nothing_when_no_matches(self) -> None:
        from cli.meta.applications.sufficient_storage import __main__ as cli_main

        with (
            patch.object(
                cli_main,
                "filter_roles_by_min_storage",
                return_value=[],
            ),
            patch.object(
                cli_main.sys,
                "argv",
                ["prog", "--roles", "web-app-a", "--required-storage", "10G"],
            ),
        ):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = cli_main.main()

        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), "")

    def test_passes_warnings_flag_through(self) -> None:
        from cli.meta.applications.sufficient_storage import __main__ as cli_main

        with (
            patch.object(
                cli_main,
                "filter_roles_by_min_storage",
                return_value=["web-app-a"],
            ) as mock_filter,
            patch.object(
                cli_main.sys,
                "argv",
                [
                    "prog",
                    "--roles",
                    "web-app-a",
                    "--required-storage",
                    "10G",
                    "--warnings",
                ],
            ),
        ):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = cli_main.main()

        self.assertEqual(rc, 0)
        mock_filter.assert_called_once()
        _, kwargs = mock_filter.call_args
        self.assertEqual(kwargs["role_names"], ["web-app-a"])
        self.assertEqual(kwargs["required_storage"], "10G")
        self.assertTrue(kwargs["emit_warnings"])


if __name__ == "__main__":
    unittest.main()
