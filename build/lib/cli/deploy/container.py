import argparse
import os
import subprocess
import sys
import time
import uuid
from typing import List, Tuple


WORKDIR_DEFAULT = "/opt/src/infinito"


def ensure_image(image: str, rebuild: bool = False, no_cache: bool = False) -> None:
    """
    Handle Docker image creation rules:
      - rebuild=True  => always rebuild
      - rebuild=False & image missing => build once
      - no_cache=True => add '--no-cache' to docker build
    """
    build_args = ["docker", "build", "--network=host", "--pull"]
    if no_cache:
        build_args.append("--no-cache")
    build_args += ["-t", image, "."]

    if rebuild:
        print(f">>> Forcing rebuild of Docker image '{image}'...")
        subprocess.run(build_args, check=True)
        print(f">>> Docker image '{image}' rebuilt (forced).")
        return

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
    subprocess.run(build_args, check=True)
    print(f">>> Docker image '{image}' successfully built.")


def docker_exec(
    container: str,
    args: List[str],
    workdir: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
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
    for _ in range(timeout):
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


def start_ci_container(
    image: str,
    build: bool,
    rebuild: bool,
    no_cache: bool,
    name: str | None = None,
) -> str:
    """
    Start a CI container running dockerd inside.

    Returns the container name.
    """
    if build or rebuild:
        ensure_image(image, rebuild=rebuild, no_cache=no_cache)

    if not name:
        name = f"infinito-ci-{uuid.uuid4().hex[:8]}"

    print(f">>> Starting CI container '{name}' with inner dockerd...")
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
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

    wait_for_inner_docker(name)
    print(f">>> CI container '{name}' started and inner dockerd is ready.")
    return name


def run_in_container(
    image: str,
    build: bool,
    rebuild: bool,
    no_cache: bool,
    inventory_args: List[str],
    deploy_args: List[str],
    name: str | None = None,
) -> None:
    """
    Full CI "run" mode:
      - start CI container with dockerd
      - run cli.create.inventory (with forwarded inventory_args)
      - ensure CI vault password file
      - run cli.deploy.dedicated (with forwarded deploy_args)
      - always remove container at the end
    """
    container_name = None
    try:
        container_name = start_ci_container(
            image=image,
            build=build,
            rebuild=rebuild,
            no_cache=no_cache,
            name=name,
        )

        # 1) Create CI inventory
        print(">>> Creating CI inventory inside container (cli.create.inventory)...")
        inventory_cmd: List[str] = [
            "python3",
            "-m",
            "cli.create.inventory",
            "inventories/github-ci",
            "--host",
            "localhost",
            "--ssl-disabled",
        ]
        inventory_cmd.extend(inventory_args)

        docker_exec(
            container_name,
            inventory_cmd,
            workdir=WORKDIR_DEFAULT,
            check=True,
        )

        # 2) Ensure vault password file exists
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
            workdir=WORKDIR_DEFAULT,
            check=True,
        )

        # 3) Run dedicated deploy
        print(">>> Running cli.deploy.dedicated inside CI container...")
        cmd = [
            "python3",
            "-m",
            "cli.deploy.dedicated",
            "inventories/github-ci/servers.yml",
            "-p",
            "inventories/github-ci/.password",
            *deploy_args,
        ]
        result = docker_exec(container_name, cmd, workdir=WORKDIR_DEFAULT, check=False)

        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd)

        print(">>> Deployment finished successfully inside CI container.")

    finally:
        if container_name:
            print(f">>> Cleaning up CI container '{container_name}'...")
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


def stop_container(name: str) -> None:
    print(f">>> Stopping container '{name}'...")
    subprocess.run(["docker", "stop", name], check=True)
    print(f">>> Container '{name}' stopped.")


def remove_container(name: str) -> None:
    print(f">>> Removing container '{name}'...")
    subprocess.run(["docker", "rm", "-f", name], check=True)
    print(f">>> Container '{name}' removed.")


def exec_in_container(name: str, cmd_args: List[str], workdir: str | None = WORKDIR_DEFAULT) -> int:
    if not cmd_args:
        print("Error: exec mode requires a command to run inside the container.", file=sys.stderr)
        return 1

    print(f">>> Executing command in container '{name}': {' '.join(cmd_args)}")
    result = docker_exec(name, cmd_args, workdir=workdir, check=False)
    return result.returncode


def split_inventory_and_deploy_args(rest: List[str]) -> Tuple[List[str], List[str]]:
    """
    Split remaining arguments into:
      - inventory_args: passed to cli.create.inventory
      - deploy_args:    passed to cli.deploy.dedicated

    Convention:
      - [inventory-args ...] -- [deploy-args ...]
      - If no '--' is present: inventory_args = [], deploy_args = all rest.
    """
    if not rest:
        return [], []

    if "--" in rest:
        idx = rest.index("--")
        inventory_args = rest[:idx]
        deploy_args = rest[idx + 1 :]
    else:
        inventory_args = []
        deploy_args = rest

    return inventory_args, deploy_args


def main() -> int:
    # Capture raw arguments without program name
    raw_argv = sys.argv[1:]

    # Split container-args vs forwarded args using first "--"
    if "--" in raw_argv:
        sep_index = raw_argv.index("--")
        container_argv = raw_argv[:sep_index]
        rest = raw_argv[sep_index + 1:]
    else:
        container_argv = raw_argv
        rest = []

    parser = argparse.ArgumentParser(
        prog="infinito-deploy-container",
        description=(
            "Run Ansible deploy inside an infinito Docker image with an inner "
            "Docker daemon (dockerd + vfs) and auto-generated CI inventory.\n\n"
            "Usage (run mode):\n"
            "  python -m cli.deploy.container run [container-opts] -- \\\n"
            "    [inventory-args ...] -- [deploy-args ...]\n\n"
            "Example:\n"
            "  python -m cli.deploy.container run --build -- \\\n"
            "    --include svc-db-mariadb -- \\\n"
            "    -T server --debug\n"
        )
    )

    parser.add_argument(
        "mode",
        choices=["run", "start", "stop", "exec", "remove"],
        help="Container mode: run, start, stop, exec, remove."
    )

    parser.add_argument("--image", default=os.environ.get("INFINITO_IMAGE", "infinito:latest"))
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--name")

    # Parse only container-level arguments
    args = parser.parse_args(container_argv)

    mode = args.mode

    # --- RUN MODE ---
    if mode == "run":
        inventory_args, deploy_args = split_inventory_and_deploy_args(rest)

        if not deploy_args:
            print(
                "Error: missing deploy arguments in run mode.\n"
                "Use:  container run [opts] -- [inventory args] -- [deploy args]",
                file=sys.stderr
            )
            return 1

        try:
            run_in_container(
                image=args.image,
                build=args.build,
                rebuild=args.rebuild,
                no_cache=args.no_cache,
                inventory_args=inventory_args,
                deploy_args=deploy_args,
                name=args.name,
            )
        except subprocess.CalledProcessError as exc:
            print(f"[ERROR] Deploy failed with exit code {exc.returncode}", file=sys.stderr)
            return exc.returncode

        return 0

    # --- START MODE ---
    if mode == "start":
        try:
            name = start_ci_container(
                image=args.image,
                build=args.build,
                rebuild=args.rebuild,
                no_cache=args.no_cache,
                name=args.name,
            )
        except Exception as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1

        print(f">>> Started CI container: {name}")
        return 0

    # For stop/remove/exec, a container name is mandatory
    if not args.name:
        print(f"Error: '{mode}' requires --name", file=sys.stderr)
        return 1

    if mode == "stop":
        stop_container(args.name)
        return 0

    if mode == "remove":
        remove_container(args.name)
        return 0

    if mode == "exec":
        return exec_in_container(args.name, rest)

    print(f"Unknown mode: {mode}", file=sys.stderr)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
