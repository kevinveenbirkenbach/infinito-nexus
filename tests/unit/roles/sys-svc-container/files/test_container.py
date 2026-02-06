from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path


# ---------------------------------------------------------------------------
# Manual import of roles/sys-svc-container/files/container.py
# ---------------------------------------------------------------------------

THIS_FILE = Path(__file__).resolve()

# tests/unit/roles/sys-svc-container/files/test_container.py -> project root
PROJECT_ROOT = THIS_FILE.parents[5]

CONTAINER_PY = PROJECT_ROOT / "roles" / "sys-svc-container" / "files" / "container.py"

if not CONTAINER_PY.exists():
    raise FileNotFoundError(f"container.py not found at {CONTAINER_PY}")

spec = importlib.util.spec_from_file_location("container", CONTAINER_PY)
container = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(container)


class TestContainerWrapper(unittest.TestCase):
    # -----------------------------------------------------------------------
    # split_docker_run_argv
    # -----------------------------------------------------------------------

    def test_split_docker_run_argv_image_only(self):
        run_opts, image_and_args = container.split_docker_run_argv(["alpine:3.20"])
        self.assertEqual(run_opts, [])
        self.assertEqual(image_and_args, ["alpine:3.20"])

    def test_split_docker_run_argv_with_flags_and_command(self):
        argv = [
            "--rm",
            "--network",
            "host",
            "-e",
            "A=B",
            "alpine:3.20",
            "sh",
            "-lc",
            "echo hi",
        ]
        run_opts, image_and_args = container.split_docker_run_argv(argv)
        self.assertEqual(run_opts, ["--rm", "--network", "host", "-e", "A=B"])
        self.assertEqual(image_and_args, ["alpine:3.20", "sh", "-lc", "echo hi"])

    def test_split_docker_run_argv_respects_double_dash(self):
        argv = ["--rm", "--", "alpine:3.20", "echo", "hi"]
        run_opts, image_and_args = container.split_docker_run_argv(argv)
        self.assertEqual(run_opts, ["--rm", "--"])
        self.assertEqual(image_and_args, ["alpine:3.20", "echo", "hi"])

    def test_split_docker_run_argv_missing_image_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            container.split_docker_run_argv(["--rm", "--network", "host"])
        self.assertEqual(ctx.exception.code, 2)

    # -----------------------------------------------------------------------
    # extract_entrypoint
    # -----------------------------------------------------------------------

    def test_extract_entrypoint_space_form(self):
        run_opts, ep = container.extract_entrypoint(
            ["--rm", "--entrypoint", "sh", "--network", "host"]
        )
        self.assertEqual(ep, "sh")
        self.assertEqual(run_opts, ["--rm", "--network", "host"])

    def test_extract_entrypoint_equals_form(self):
        run_opts, ep = container.extract_entrypoint(
            ["--rm", "--entrypoint=sh", "--network", "host"]
        )
        self.assertEqual(ep, "sh")
        self.assertEqual(run_opts, ["--rm", "--network", "host"])

    # -----------------------------------------------------------------------
    # extract_pull_policy
    # -----------------------------------------------------------------------

    def test_extract_pull_policy_default(self):
        self.assertEqual(container.extract_pull_policy(["--rm"]), "missing")

    def test_extract_pull_policy_variants(self):
        cases = [
            (["--rm", "--pull", "always"], "always"),
            (["--rm", "--pull=always"], "always"),
            (["--rm", "--pull", "never"], "never"),
            (["--rm", "--pull=missing"], "missing"),
            (["--rm", "--pull", "invalid"], "missing"),
        ]
        for opts, expected in cases:
            with self.subTest(opts=opts):
                self.assertEqual(container.extract_pull_policy(opts), expected)

    # -----------------------------------------------------------------------
    # try_inspect_entrypoint_with_pull
    # -----------------------------------------------------------------------

    def test_try_inspect_entrypoint_pull_always(self):
        calls = []

        def fake_pull(image: str) -> None:
            calls.append(("pull", image))

        def fake_inspect(image: str):
            calls.append(("inspect", image))
            return ["/entrypoint"]

        orig_pull = container.docker_pull
        orig_inspect = container.inspect_image_entrypoint
        try:
            container.docker_pull = fake_pull
            container.inspect_image_entrypoint = fake_inspect

            ep = container.try_inspect_entrypoint_with_pull(
                "alpine:3.20",
                pull_policy="always",
            )
            self.assertEqual(ep, ["/entrypoint"])
            self.assertEqual(
                calls,
                [("pull", "alpine:3.20"), ("inspect", "alpine:3.20")],
            )
        finally:
            container.docker_pull = orig_pull
            container.inspect_image_entrypoint = orig_inspect

    def test_try_inspect_entrypoint_pull_missing_recovers(self):
        calls = []

        def inspect_fail(image: str):
            calls.append(("inspect_fail", image))
            raise SystemExit(2)

        def inspect_ok(image: str):
            calls.append(("inspect_ok", image))
            return ["/entrypoint"]

        def fake_pull(image: str) -> None:
            calls.append(("pull", image))
            # swap inspect to succeed after pull
            container.inspect_image_entrypoint = inspect_ok

        class FakeCompleted:
            def __init__(self):
                self.returncode = 1
                self.stdout = ""
                self.stderr = "No such image: alpine:3.20"

        def fake_run(*_args, **_kwargs):
            calls.append(("subprocess.run",))
            return FakeCompleted()

        orig_pull = container.docker_pull
        orig_inspect = container.inspect_image_entrypoint
        orig_run = subprocess.run
        try:
            container.inspect_image_entrypoint = inspect_fail
            container.docker_pull = fake_pull
            subprocess.run = fake_run  # used only in recovery path

            ep = container.try_inspect_entrypoint_with_pull(
                "alpine:3.20",
                pull_policy="missing",
            )

            self.assertEqual(ep, ["/entrypoint"])
            self.assertEqual(
                calls,
                [
                    ("inspect_fail", "alpine:3.20"),
                    ("subprocess.run",),
                    ("pull", "alpine:3.20"),
                    ("inspect_ok", "alpine:3.20"),
                ],
            )
        finally:
            container.docker_pull = orig_pull
            container.inspect_image_entrypoint = orig_inspect
            subprocess.run = orig_run

    def test_try_inspect_entrypoint_pull_never_fails(self):
        def inspect_fail(_image: str):
            raise SystemExit(2)

        orig_inspect = container.inspect_image_entrypoint
        try:
            container.inspect_image_entrypoint = inspect_fail

            with self.assertRaises(SystemExit) as ctx:
                container.try_inspect_entrypoint_with_pull(
                    "alpine:3.20",
                    pull_policy="never",
                )
            self.assertEqual(ctx.exception.code, 2)
        finally:
            container.inspect_image_entrypoint = orig_inspect


if __name__ == "__main__":
    unittest.main()
