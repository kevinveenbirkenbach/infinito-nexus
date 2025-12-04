# cli/deploy/container.py
import argparse
import os
import subprocess
import sys
import time
import uuid
from typing import List


def ensure_image(image: str) -> None:
    """
    Ensure the Docker image exists locally. If not, build it with docker build.
    """
    print(f">>> Checking if Docker image '{image}' exists...")
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode == 0:
        print(f">>> Docker image '{image}' already exists.")
        return

    print(f">>> Docker image '{image}' not found. Building it...")
    subprocess.run(
        ["docker", "build", "--network=host", "--pull", "-t", image, "."],
        check=True,
    )
    print(f">>> Docker image '{image}' successfully built.")


def docker_exec(container: str, args: List[str], workdir: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """
    Helper to run `docker exec` with optional working directory.
    """
    cmd = ["docker", "exec"]
    if workdir:
        cmd += ["-w", workdir]
    cmd.append(container)
    cmd += args

    return subprocess.run(cmd, check=check)


def wait_for_inner_docker(container: str, timeout: int = 60) -> None:
    """
    Poll `docker exec <container> docker info` until inner dockerd is ready.
    """
    print(">>> Waiting for inner Docker daemon inside CI container...")
    for i in range(timeout):
        result = subprocess.run(
            ["docker", "exec", container, "docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            print(">>> Inner Docker daemon is UP.")
            return
        time.sleep(1)

    raise RuntimeError("Inner Docker daemon did not become ready in time")


def run_in_container(
    image: str,
    exclude: str,
    forwarded_args: List[str],
    build: bool,
) -> None:
    """
    Orchestrate everything from the *host*:
      - start CI container with inner dockerd
      - wait for inner docker
      - create inventory (cli.create.inventory)
      - ensure vault password file
      - run cli.deploy.dedicated
    All heavy lifting inside the container happens via direct `docker exec` calls.
    """
    if build:
        ensure_image(image)

    container_name = f"infinito-ci-{uuid.uuid4().hex[:8]}"
    workdir = "/opt/infinito-src"

    try:
        # 1) Start CI container with dockerd as PID 1
        print(f">>> Starting CI container '{container_name}' with inner dockerd...")
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "--network=host",
                "--privileged",
                "--cgroupns=host",
                image,
                "dockerd",
                "--debug",
                "--host=unix:///var/run/docker.sock",
                "--storage-driver=vfs",
            ],
            check=True,
        )

        # 2) Wait until inner docker responds
        wait_for_inner_docker(container_name)

        # 3) Create CI inventory via Python module
        print(">>> Creating CI inventory inside container (cli.create.inventory)...")
        docker_exec(
            container_name,
            [
                "python3",
                "-m",
                "cli.create.inventory",
                "inventories/github-ci",
                "--host",
                "localhost",
                "--exclude",
                exclude,
                "--ssl-disabled",
            ],
            workdir=workdir,
            check=True,
        )

        # 4) Ensure vault password file exists
        print(">>> Ensuring CI vault password file exists...")
        docker_exec(
            container_name,
            [
                "sh",
                "-c",
                "mkdir -p inventories/github-ci && "
                "[ -f inventories/github-ci/.password ] || "
                "printf '%s\n' 'ci-vault-password' > inventories/github-ci/.password",
            ],
            workdir=workdir,
            check=True,
        )

        # 5) Run dedicated deploy
        print(">>> Running cli.deploy.dedicated inside CI container...")
        cmd = [
            "python3",
            "-m",
            "cli.deploy.dedicated",
            "inventories/github-ci/servers.yml",
            "-p",
            "inventories/github-ci/.password",
            *forwarded_args,
        ]
        result = docker_exec(container_name, cmd, workdir=workdir, check=False)

        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd
            )

        print(">>> Deployment finished successfully inside CI container.")

    finally:
        print(f">>> Cleaning up CI container '{container_name}'...")
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="infinito-deploy-container",
        description=(
            "Run cli.deploy.dedicated inside an infinito Docker image with an inner "
            "Docker daemon (dockerd + vfs) and auto-generated CI inventory."
        ),
    )

    parser.add_argument(
        "--image",
        default=os.environ.get("INFINITO_IMAGE", "infinito:latest"),
        help="Docker image to use (default: %(default)s, overridable via INFINITO_IMAGE).",
    )

    parser.add_argument(
        "--exclude",
        default=os.environ.get("EXCLUDED_ROLES", ""),
        help=(
            "Comma-separated list of roles to exclude when creating the CI inventory "
            "(default taken from EXCLUDED_ROLES env var)."
        ),
    )

    parser.add_argument(
        "--build",
        action="store_true",
        help="If set, ensure the Docker image exists by building it when missing.",
    )

    parser.add_argument(
        "forwarded",
        nargs=argparse.REMAINDER,
        help=(
            "Arguments to forward to cli.deploy.dedicated. "
            "Use '--' to separate wrapper options from dedicated options."
        ),
    )

    args = parser.parse_args()

    forwarded_args = list(args.forwarded)
    if forwarded_args and forwarded_args[0] == "--":
        forwarded_args = forwarded_args[1:]

    if not forwarded_args:
        print(
            "Error: no arguments forwarded to dedicated deploy script.\n"
            "Hint: use '--' to separate wrapper options from dedicated options, e.g.\n"
            "  python -m cli.deploy.container --build -- -T server --debug --skip-tests",
            file=sys.stderr,
        )
        return 1

    try:
        run_in_container(
            image=args.image,
            exclude=args.exclude,
            forwarded_args=forwarded_args,
            build=args.build,
        )
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] Container run failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
