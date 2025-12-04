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
        """
        If the image already exists, ensure_image should only call
        `docker image inspect` and NOT run `docker build`.
        """
        # docker image inspect → rc=0 (image exists)
        mock_run.return_value = subprocess.CompletedProcess(
            args=["docker", "image", "inspect", "infinito:latest"],
            returncode=0,
            stdout="",
            stderr="",
        )

        deploy_container.ensure_image("infinito:latest")

        # Exactly one call: docker image inspect
        self.assertEqual(mock_run.call_count, 1)
        cmd = mock_run.call_args_list[0].args[0]
        self.assertEqual(cmd[:3], ["docker", "image", "inspect"])

        # Ensure docker build was never called
        self.assertFalse(
            any(
                call.args[0][:2] == ["docker", "build"]
                for call in mock_run.call_args_list
            ),
            "docker build should not run when the image already exists",
        )

    @mock.patch("subprocess.run")
    def test_ensure_image_builds_when_missing(self, mock_run):
        """
        If the image does not exist, ensure_image should call
        `docker image inspect` first and then `docker build`.
        """
        calls: List[List[str]] = []

        def _side_effect(cmd, *args, **kwargs):
            calls.append(cmd)

            # First: docker image inspect → rc=1 (missing)
            if cmd[:3] == ["docker", "image", "inspect"]:
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=1,
                    stdout="",
                    stderr="missing",
                )

            # Then: docker build → rc=0 (success)
            if cmd[:2] == ["docker", "build"]:
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=0,
                    stdout="",
                    stderr="",
                )

            # Any other commands (should not happen here)
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )

        mock_run.side_effect = _side_effect

        deploy_container.ensure_image("infinito:latest")

        self.assertTrue(
            any(c[:3] == ["docker", "image", "inspect"] for c in calls),
            "Expected 'docker image inspect' to be called",
        )
        self.assertTrue(
            any(c[:2] == ["docker", "build"] for c in calls),
            "Expected 'docker build' to run when image is missing",
        )


class TestRunInContainer(unittest.TestCase):
    @mock.patch("subprocess.run")
    def test_run_in_container_calls_single_docker_run(self, mock_run):
        """
        run_in_container should start exactly one 'docker run' CI container,
        then use docker exec for everything else.
        """
        calls: List[List[str]] = []

        def _side_effect(cmd, *args, **kwargs):
            calls.append(cmd)
            # Always succeed → wait_for_inner_docker stops on first call
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )

        mock_run.side_effect = _side_effect

        image = "infinito:latest"
        inventory_args = ["--include", "svc-db-mariadb"]
        deploy_args = ["-T", "server", "--debug", "--skip-tests"]

        deploy_container.run_in_container(
            image=image,
            build=False,
            rebuild=False,
            no_cache=False,
            inventory_args=inventory_args,
            deploy_args=deploy_args,
            name=None,
        )

        # At least one command must have been executed
        self.assertGreaterEqual(len(calls), 1)

        # Filter all docker run invocations
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
            "Expected exactly one 'docker run' call (for the CI container)",
        )

        cmd = docker_run_calls[0]
        self.assertEqual(cmd[0], "docker")
        self.assertEqual(cmd[1], "run")
        self.assertIn("-d", cmd)
        self.assertIn("--name", cmd)
        self.assertIn("--network=host", cmd)
        self.assertIn("--privileged", cmd)
        self.assertIn("--cgroupns=host", cmd)
        self.assertIn(image, cmd)
        self.assertIn("dockerd", cmd)


class TestMain(unittest.TestCase):
    @mock.patch("cli.deploy.container.run_in_container")
    def test_main_requires_forwarded_args(self, mock_run_in_container):
        """
        In 'run' mode, main() must return 1 and not call run_in_container()
        if no deploy arguments are provided after the first '--'.
        """
        argv = [
            "cli.deploy.container",
            "run",
            "--image",
            "myimage:latest",
            "--build",
            "--",
            # no inventory/deploy args here
        ]
        with mock.patch.object(sys, "argv", argv):
            rc = deploy_container.main()

        self.assertEqual(rc, 1)
        mock_run_in_container.assert_not_called()

    @mock.patch("cli.deploy.container.run_in_container")
    def test_main_passes_arguments_to_run_in_container(self, mock_run_in_container):
        """
        Ensure that main() correctly splits container args vs inventory/deploy
        args and passes them to run_in_container().
        """
        argv = [
            "cli.deploy.container",
            "run",
            "--image",
            "myimage:latest",
            "--build",
            "--",
            "--exclude",
            "foo,bar",
            "--",
            "-T",
            "server",
            "--debug",
        ]

        with mock.patch.object(sys, "argv", argv):
            rc = deploy_container.main()

        self.assertEqual(rc, 0)
        mock_run_in_container.assert_called_once()

        kwargs = mock_run_in_container.call_args.kwargs

        # Container-level options
        self.assertEqual(kwargs["image"], "myimage:latest")
        self.assertTrue(kwargs["build"])
        self.assertFalse(kwargs["rebuild"])
        self.assertFalse(kwargs["no_cache"])
        self.assertIsNone(kwargs["name"])

        # Inventory args: first segment after first '--' until second '--'
        self.assertEqual(
            kwargs["inventory_args"],
            ["--exclude", "foo,bar"],
        )

        # Deploy args: everything after the second '--'
        self.assertEqual(
            kwargs["deploy_args"],
            ["-T", "server", "--debug"],
        )


if __name__ == "__main__":
    unittest.main()
