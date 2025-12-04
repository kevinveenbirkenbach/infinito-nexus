# tests/unit/cli/deploy/test_container.py
import subprocess
import sys
import unittest
from typing import List
from unittest import mock

from cli.deploy import container as deploy_container


class TestEnsureImage(unittest.TestCase):
    @mock.patch("subprocess.run")
    def test_ensure_image_skips_build_when_image_exists(self, mock_run):
        # docker image inspect → returncode 0 means "image exists"
        mock_run.return_value = subprocess.CompletedProcess(
            ["docker", "image", "inspect", "infinito:latest"],
            0,
            stdout=b"",
            stderr=b"",
        )

        deploy_container.ensure_image("infinito:latest")

        # Only one call: docker image inspect
        self.assertEqual(mock_run.call_count, 1)
        cmd = mock_run.call_args_list[0].args[0]
        self.assertEqual(cmd[:3], ["docker", "image", "inspect"])

        # No docker build command
        self.assertFalse(
            any(
                call.args[0][:2] == ["docker", "build"]
                for call in mock_run.call_args_list
            ),
            "docker build should not run when the image already exists",
        )

    @mock.patch("subprocess.run")
    def test_ensure_image_builds_when_missing(self, mock_run):
        calls: List[List[str]] = []

        def _side_effect(cmd, *args, **kwargs):
            calls.append(cmd)
            # First inspect fails → triggers build
            if cmd[:3] == ["docker", "image", "inspect"]:
                return subprocess.CompletedProcess(cmd, 1, b"", b"missing")
            # Build succeeds
            if cmd[:2] == ["docker", "build"]:
                return subprocess.CompletedProcess(cmd, 0, b"", b"")
            return subprocess.CompletedProcess(cmd, 0, b"", b"")

        mock_run.side_effect = _side_effect

        deploy_container.ensure_image("infinito:latest")

        self.assertTrue(
            any(c[:3] == ["docker", "image", "inspect"] for c in calls),
            "Expected docker image inspect to be called",
        )
        self.assertTrue(
            any(c[:2] == ["docker", "build"] for c in calls),
            "Expected docker build to run when image is missing",
        )

class TestRunInContainer(unittest.TestCase):
    @mock.patch("subprocess.run")
    def test_run_in_container_calls_single_docker_run(self, mock_run):
        """
        Current container.py starts exactly one Docker container via
        'docker run' to launch the inner dockerd daemon. All further work
        (inventory creation + dedicated deploy) happens via docker exec.
        """
        calls: List[List[str]] = []

        def _side_effect(cmd, *args, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, b"", b"")

        mock_run.side_effect = _side_effect

        image = "infinito:latest"
        exclude = "foo,bar"
        forwarded = ["-T", "server", "--debug", "--skip-tests"]

        deploy_container.run_in_container(
            image=image,
            exclude=exclude,
            forwarded_args=forwarded,
            build=False,
        )

        # We expect at least one subprocess.run call
        self.assertGreaterEqual(len(calls), 1)

        # Only count *docker run* invocations, not docker exec / image / build
        docker_run_calls = [
            c
            for c in calls
            if isinstance(c, list)
            and len(c) >= 2
            and c[0] == "docker"
            and c[1] == "run"
        ]

        self.assertEqual(
            len(docker_run_calls),
            1,
            "Expected exactly one 'docker run' call",
        )

        cmd = docker_run_calls[0]

        # Basic structure of the docker run call
        self.assertEqual(cmd[0], "docker")
        self.assertEqual(cmd[1], "run")

        # New behavior: container runs dockerd in detached mode
        self.assertIn("-d", cmd)
        self.assertIn("--name", cmd)
        self.assertIn("--network=host", cmd)
        self.assertIn("--privileged", cmd)
        self.assertIn("--cgroupns=host", cmd)
        self.assertIn(image, cmd)
        self.assertIn("dockerd", cmd)

        # We *no longer* expect '--rm', '/bin/sh', or '-lc' here,
        # because all higher-level logic is executed by docker exec.


class TestMain(unittest.TestCase):
    @mock.patch("cli.deploy.container.run_in_container")
    def test_main_requires_forwarded_args(self, mock_run_in_container):
        """
        If no arguments follow '--', main() must return exit code 1 and not call run_in_container().
        """
        argv = ["cli.deploy.container"]  # realistic argv from `python -m ...`
        with mock.patch.object(sys, "argv", argv):
            rc = deploy_container.main()

        self.assertEqual(rc, 1)
        mock_run_in_container.assert_not_called()

    @mock.patch("cli.deploy.container.run_in_container")
    def test_main_passes_arguments_to_run_in_container(self, mock_run_in_container):
        """
        Ensure CLI args are parsed and forwarded correctly.
        """
        argv = [
            "cli.deploy.container",
            "--image", "myimage:latest",
            "--exclude", "foo,bar",
            "--build",
            "--",
            "-T", "server",
            "--debug",
        ]

        with mock.patch.object(sys, "argv", argv):
            rc = deploy_container.main()

        self.assertEqual(rc, 0)
        mock_run_in_container.assert_called_once()

        # access kwargs passed to run_in_container
        kwargs = mock_run_in_container.call_args.kwargs

        self.assertEqual(kwargs["image"], "myimage:latest")
        self.assertEqual(kwargs["exclude"], "foo,bar")  # <-- fixed key
        self.assertTrue(kwargs["build"])
        self.assertEqual(
            kwargs["forwarded_args"],
            ["-T", "server", "--debug"],
        )


if __name__ == "__main__":
    unittest.main()
