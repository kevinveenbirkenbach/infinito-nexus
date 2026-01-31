#!/usr/bin/env python3
"""
Unit tests for roles/sys-svc-docker/files/run.py

These tests:
- avoid calling real docker
- validate argv parsing and final docker command composition
- cover --entrypoint passthrough and default image entrypoint discovery
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


def load_script_module():
    """
    Import the script under test from roles/sys-svc-docker/files/run.py.
    """
    test_file = Path(__file__).resolve()
    repo_root = test_file.parents[
        5
    ]  # .../tests/unit/roles/sys-svc-docker/files -> repo root
    script_path = repo_root / "roles" / "sys-svc-docker" / "files" / "run.py"
    if not script_path.exists():
        raise FileNotFoundError(f"run.py not found at {script_path}")
    spec = importlib.util.spec_from_file_location("run_wrapper", str(script_path))
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


class _ExecvpCalled(Exception):
    def __init__(self, cmd0: str, argv: list[str]):
        super().__init__("execvp called")
        self.cmd0 = cmd0
        self.argv = argv


class TestRunWrapper(unittest.TestCase):
    def setUp(self) -> None:
        self.s = load_script_module()

    def _fake_execvp(self, cmd0, argv):
        raise _ExecvpCalled(cmd0, list(argv))

    def _patch_common(self, *, image_entrypoint_json: str | None):
        """
        Patch env + must_exist + docker inspect + execvp.
        """
        # fake env required by wrapper
        env = {
            "CA_TRUST_CERT_HOST": "/host/ca.crt",
            "CA_TRUST_WRAPPER_HOST": "/host/with-ca-trust.sh",
            "CA_TRUST_NAME": "infinito.example",
        }

        # must_exist: just return the given path (pretend exists)
        def must_exist_passthrough(path, label):
            return path

        # mock subprocess.run used by inspect_image_entrypoint
        def fake_subprocess_run(argv, check, capture_output, text):
            # Expect: docker image inspect IMAGE --format {{json .Config.Entrypoint}}
            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            r = R()
            if "image" in argv and "inspect" in argv:
                if image_entrypoint_json is None:
                    r.stdout = "null"
                else:
                    r.stdout = image_entrypoint_json
                return r
            # Anything else is unexpected here
            r.returncode = 2
            r.stderr = "unexpected subprocess.run call"
            return r

        patches = [
            patch.object(self.s.os, "execvp", side_effect=self._fake_execvp),
            patch.object(self.s, "must_exist", side_effect=must_exist_passthrough),
            patch.object(self.s.os, "environ", env, create=True),
            patch.object(self.s.subprocess, "run", side_effect=fake_subprocess_run),
        ]
        return patches

    def test_missing_required_env(self):
        # Clear env
        with patch.object(self.s.os, "environ", {}, create=True):
            with self.assertRaises(SystemExit) as cm:
                with patch.object(self.s.sys, "argv", ["run.py", "alpine:3.19"]):
                    self.s.main()
            self.assertEqual(cm.exception.code, 2)

    def test_missing_image_argument(self):
        patches = self._patch_common(image_entrypoint_json='["node","health-csp.js"]')
        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(SystemExit) as cm:
                with patch.object(self.s.sys, "argv", ["run.py"]):
                    self.s.main()
            self.assertEqual(cm.exception.code, 2)

    def test_default_entrypoint_used_when_no_user_entrypoint(self):
        # Image ENTRYPOINT is ["node","health-csp.js"]
        patches = self._patch_common(image_entrypoint_json='["node","health-csp.js"]')

        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(_ExecvpCalled) as cm:
                with patch.object(
                    self.s.sys,
                    "argv",
                    [
                        "run.py",
                        "--rm",
                        "--network",
                        "host",
                        "ghcr.io/x/y:stable",
                        "--short",
                        "https://a/",
                    ],
                ):
                    self.s.main()

            call = cm.exception
            self.assertEqual(call.cmd0, "docker")
            argv = call.argv

            # Must begin with docker run
            self.assertEqual(argv[0:2], ["docker", "run"])

            # user opts preserved before inject opts
            self.assertIn("--rm", argv)
            self.assertIn("--network", argv)
            self.assertIn("host", argv)

            # injection opts present
            self.assertIn("-v", argv)
            self.assertIn("/host/ca.crt:/tmp/infinito/ca/root-ca.crt:ro", argv)
            self.assertIn(
                "/host/with-ca-trust.sh:/tmp/infinito/bin/with-ca-trust.sh:ro", argv
            )
            self.assertIn("-e", argv)
            self.assertIn("CA_TRUST_CERT=/tmp/infinito/ca/root-ca.crt", argv)
            self.assertIn("CA_TRUST_NAME=infinito.example", argv)
            self.assertIn("--entrypoint", argv)

            # After IMAGE, should run: node health-csp.js --short https://a/
            # Find image index
            img_i = argv.index("ghcr.io/x/y:stable")
            tail = argv[img_i + 1 :]
            self.assertEqual(tail[0:2], ["node", "health-csp.js"])
            self.assertIn("--short", tail)
            self.assertIn("https://a/", tail)

    def test_user_entrypoint_overrides_image_entrypoint(self):
        patches = self._patch_common(image_entrypoint_json='["node","health-csp.js"]')

        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(_ExecvpCalled) as cm:
                with patch.object(
                    self.s.sys,
                    "argv",
                    [
                        "run.py",
                        "--rm",
                        "--entrypoint",
                        "sh",
                        "ghcr.io/x/y:stable",
                        "-lc",
                        "echo ok",
                    ],
                ):
                    self.s.main()

            argv = cm.exception.argv
            img_i = argv.index("ghcr.io/x/y:stable")
            tail = argv[img_i + 1 :]

            # Must execute user entrypoint + user args (not node health-csp.js)
            self.assertEqual(tail[0], "sh")
            self.assertEqual(tail[1], "-lc")
            self.assertEqual(tail[2], "echo ok")

    def test_entrypoint_equals_form_supported(self):
        patches = self._patch_common(image_entrypoint_json='["node","health-csp.js"]')

        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(_ExecvpCalled) as cm:
                with patch.object(
                    self.s.sys,
                    "argv",
                    [
                        "run.py",
                        "--rm",
                        "--entrypoint=sh",
                        "ghcr.io/x/y:stable",
                        "-lc",
                        "echo ok",
                    ],
                ):
                    self.s.main()

            argv = cm.exception.argv
            img_i = argv.index("ghcr.io/x/y:stable")
            tail = argv[img_i + 1 :]
            self.assertEqual(tail[0], "sh")
            self.assertEqual(tail[1], "-lc")
            self.assertEqual(tail[2], "echo ok")

    def test_image_without_entrypoint_and_no_user_entrypoint_errors(self):
        # Image has no ENTRYPOINT (null)
        patches = self._patch_common(image_entrypoint_json="null")

        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(SystemExit) as cm:
                with patch.object(
                    self.s.sys, "argv", ["run.py", "--rm", "alpine:3.19"]
                ):
                    self.s.main()
            self.assertEqual(cm.exception.code, 2)

    def test_flag_value_parsing(self):
        """
        Ensure options that take values are consumed correctly and IMAGE detection works.
        """
        patches = self._patch_common(image_entrypoint_json='["node","health-csp.js"]')

        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(_ExecvpCalled) as cm:
                with patch.object(
                    self.s.sys,
                    "argv",
                    [
                        "run.py",
                        "--rm",
                        "-e",
                        "FOO=bar",
                        "-v",
                        "/x:/y:ro",
                        "--name",
                        "test1",
                        "ghcr.io/x/y:stable",
                        "--short",
                        "https://a/",
                    ],
                ):
                    self.s.main()

            argv = cm.exception.argv
            # Ensure the injected opts are still present and the user's -e/-v are not mistaken as IMAGE.
            self.assertIn("ghcr.io/x/y:stable", argv)
            self.assertIn("FOO=bar", argv)
            self.assertIn("/x:/y:ro", argv)
            self.assertIn("test1", argv)


if __name__ == "__main__":
    unittest.main()
