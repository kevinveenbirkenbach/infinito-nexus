#!/usr/bin/env python3
"""
Unit tests for roles/sys-svc-docker/files/run.py

These tests:
- avoid calling real docker
- validate argv parsing and final docker command composition
- cover --entrypoint passthrough and default image entrypoint discovery
- cover pull-on-missing logic added to avoid failing on docker image inspect when image is absent
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

        This helper assumes docker image inspect succeeds (returncode=0).
        """
        env = {
            "CA_TRUST_CERT_HOST": "/host/ca.crt",
            "CA_TRUST_WRAPPER_HOST": "/host/with-ca-trust.sh",
            "CA_TRUST_NAME": "infinito.example",
        }

        def must_exist_passthrough(path, label):
            return path

        def fake_subprocess_run(argv, check, capture_output, text):
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

    def _patch_pull_scenario(
        self,
        *,
        image: str,
        entrypoint_json_after: str,
        inspect_missing_first: bool,
        pull_rc: int = 0,
        pull_stderr: str = "",
        inspect_missing_msg: str | None = None,
    ):
        """
        Patch env + must_exist + docker inspect (optionally missing on first call) + docker pull + execvp.

        Note: The current wrapper implementation performs *two* inspect calls when the first one fails:
          - initial inspect (inside inspect_image_entrypoint)
          - "probe" inspect (inside try_inspect_entrypoint_with_pull to read the error message)
        Therefore, when simulating a missing image, we must return "No such image" for BOTH
        the initial inspect and the probe inspect.
        """
        env = {
            "CA_TRUST_CERT_HOST": "/host/ca.crt",
            "CA_TRUST_WRAPPER_HOST": "/host/with-ca-trust.sh",
            "CA_TRUST_NAME": "infinito.example",
        }

        def must_exist_passthrough(path, label):
            return path

        call_history: list[list[str]] = []
        flags = {"pull_called": 0, "inspect_called": 0}

        missing_msg = (
            inspect_missing_msg
            if inspect_missing_msg is not None
            else f"Error response from daemon: No such image: {image}"
        )

        def fake_subprocess_run(argv, check, capture_output, text):
            call_history.append(list(argv))

            class R:
                returncode = 0
                stdout = ""
                stderr = ""

            r = R()

            if len(argv) >= 3 and argv[0:2] == ["docker", "pull"] and argv[2] == image:
                flags["pull_called"] += 1
                r.returncode = pull_rc
                r.stderr = pull_stderr
                return r

            if (
                len(argv) >= 6
                and argv[0:3] == ["docker", "image", "inspect"]
                and argv[3] == image
            ):
                flags["inspect_called"] += 1

                # IMPORTANT: simulate missing image for the first TWO inspect calls:
                # 1) initial inspect
                # 2) probe inspect
                if inspect_missing_first and flags["inspect_called"] in (1, 2):
                    r.returncode = 1
                    r.stderr = missing_msg
                    r.stdout = ""
                    return r

                r.returncode = 0
                r.stdout = entrypoint_json_after
                r.stderr = ""
                return r

            r.returncode = 2
            r.stderr = "unexpected subprocess.run call"
            return r

        patches = [
            patch.object(self.s.os, "execvp", side_effect=self._fake_execvp),
            patch.object(self.s, "must_exist", side_effect=must_exist_passthrough),
            patch.object(self.s.os, "environ", env, create=True),
            patch.object(self.s.subprocess, "run", side_effect=fake_subprocess_run),
        ]
        return patches, call_history, flags

    def test_missing_required_env(self):
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

            self.assertEqual(argv[0:2], ["docker", "run"])

            self.assertIn("--rm", argv)
            self.assertIn("--network", argv)
            self.assertIn("host", argv)

            self.assertIn("-v", argv)
            self.assertIn("/host/ca.crt:/tmp/infinito/ca/root-ca.crt:ro", argv)
            self.assertIn(
                "/host/with-ca-trust.sh:/tmp/infinito/bin/with-ca-trust.sh:ro", argv
            )
            self.assertIn("-e", argv)
            self.assertIn("CA_TRUST_CERT=/tmp/infinito/ca/root-ca.crt", argv)
            self.assertIn("CA_TRUST_NAME=infinito.example", argv)
            self.assertIn("--entrypoint", argv)

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
        patches = self._patch_common(image_entrypoint_json="null")

        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(SystemExit) as cm:
                with patch.object(self.s.sys, "argv", ["run.py", "--rm", "alpine:3.19"]):
                    self.s.main()
            self.assertEqual(cm.exception.code, 2)

    def test_flag_value_parsing(self):
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
            self.assertIn("ghcr.io/x/y:stable", argv)
            self.assertIn("FOO=bar", argv)
            self.assertIn("/x:/y:ro", argv)
            self.assertIn("test1", argv)

    # -------------------------------------------------------------------------
    # New tests for pull logic
    # -------------------------------------------------------------------------

    def test_pull_on_missing_default_policy_pulls_then_execs(self):
        """
        New logic: if docker image inspect fails because the image is missing,
        the wrapper should pull the image (default policy is "missing") and retry inspect.
        """
        image = "ghcr.io/x/y:stable"
        patches, call_history, flags = self._patch_pull_scenario(
            image=image,
            entrypoint_json_after='["node","health-csp.js"]',
            inspect_missing_first=True,
        )

        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(_ExecvpCalled) as cm:
                with patch.object(
                    self.s.sys,
                    "argv",
                    [
                        "run.py",
                        "--rm",
                        image,
                        "--short",
                        "https://a/",
                    ],
                ):
                    self.s.main()

            # With the current wrapper, expect:
            # inspect (fail) + inspect(probe fail) + pull + inspect(success)
            self.assertEqual(flags["pull_called"], 1)
            self.assertEqual(flags["inspect_called"], 3)

            flattened = [" ".join(x) for x in call_history]
            self.assertTrue(any(s.startswith("docker pull") for s in flattened))

            argv = cm.exception.argv
            self.assertEqual(argv[0:2], ["docker", "run"])
            self.assertIn(image, argv)

            img_i = argv.index(image)
            tail = argv[img_i + 1 :]
            self.assertEqual(tail[0:2], ["node", "health-csp.js"])
            self.assertIn("--short", tail)
            self.assertIn("https://a/", tail)

    def test_pull_never_policy_does_not_pull_and_fails_on_missing(self):
        """
        New logic: with --pull=never, the wrapper must not attempt to pull.
        If image inspect fails because image is missing, it should exit with code 2.
        """
        image = "ghcr.io/x/y:stable"
        patches, call_history, flags = self._patch_pull_scenario(
            image=image,
            entrypoint_json_after='["node","health-csp.js"]',
            inspect_missing_first=True,
        )

        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(SystemExit) as cm:
                with patch.object(
                    self.s.sys,
                    "argv",
                    [
                        "run.py",
                        "--rm",
                        "--pull=never",
                        image,
                        "--short",
                        "https://a/",
                    ],
                ):
                    self.s.main()

            self.assertEqual(cm.exception.code, 2)
            self.assertEqual(flags["pull_called"], 0)

            flattened = [" ".join(x) for x in call_history]
            self.assertFalse(any(s.startswith("docker pull") for s in flattened))

    def test_pull_always_policy_pulls_before_inspect(self):
        """
        New logic: with --pull=always, the wrapper must pull before inspecting entrypoint.
        """
        image = "ghcr.io/x/y:stable"
        patches, call_history, flags = self._patch_pull_scenario(
            image=image,
            entrypoint_json_after='["node","health-csp.js"]',
            inspect_missing_first=False,
        )

        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(_ExecvpCalled):
                with patch.object(
                    self.s.sys,
                    "argv",
                    [
                        "run.py",
                        "--rm",
                        "--pull=always",
                        image,
                        "--short",
                        "https://a/",
                    ],
                ):
                    self.s.main()

            self.assertEqual(flags["pull_called"], 1)
            self.assertGreaterEqual(flags["inspect_called"], 1)

            self.assertGreaterEqual(len(call_history), 1)
            self.assertEqual(call_history[0][0:3], ["docker", "pull", image])

    def test_pull_always_policy_fails_if_pull_fails(self):
        """
        New logic: with --pull=always, a pull failure should fail hard (exit code 2).
        """
        image = "ghcr.io/x/y:stable"
        patches, call_history, flags = self._patch_pull_scenario(
            image=image,
            entrypoint_json_after='["node","health-csp.js"]',
            inspect_missing_first=False,
            pull_rc=1,
            pull_stderr="permission denied",
        )

        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(SystemExit) as cm:
                with patch.object(
                    self.s.sys,
                    "argv",
                    [
                        "run.py",
                        "--rm",
                        "--pull=always",
                        image,
                        "--short",
                        "https://a/",
                    ],
                ):
                    self.s.main()

            self.assertEqual(cm.exception.code, 2)
            self.assertEqual(flags["pull_called"], 1)

            flattened = [" ".join(x) for x in call_history]
            self.assertTrue(any(s.startswith("docker pull") for s in flattened))


if __name__ == "__main__":
    unittest.main()
