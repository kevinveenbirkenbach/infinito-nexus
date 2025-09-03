#!/usr/bin/env python3
"""
Restart Docker-Compose configurations with exited or unhealthy containers.

STRICT mode: Resolve the Compose project exclusively via Docker labels
(com.docker.compose.project and com.docker.compose.project.working_dir).
No container-name fallback. If labels are missing or Docker is unavailable,
the script records an error for that container.

All shell interactions that matter for tests go through print_bash()
so they can be monkeypatched in unit tests.
"""
import subprocess
import time
import os
import argparse
from typing import List, Optional, Tuple


# ---------------------------
# Shell helpers
# ---------------------------

def bash(command: str) -> List[str]:
    print(command)
    process = subprocess.Popen(
        [command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
    )
    out, err = process.communicate()
    stdout = out.splitlines()
    stderr = err.decode("utf-8", errors="replace").strip()
    output = [line.decode("utf-8", errors="replace") for line in stdout]
    if process.returncode > 0:
        print(command, out, err)
        raise Exception(stderr or f"Command failed with code {process.returncode}")
    return output


def list_to_string(lst: List[str]) -> str:
    return " ".join(lst)


def print_bash(command: str) -> List[str]:
    """
    Wrapper around bash() that echoes combined output for easier debugging
    and can be monkeypatched in tests.
    """
    output = bash(command)
    if output:
        print(list_to_string(output))
    return output


# ---------------------------
# Filesystem / compose helpers
# ---------------------------

def find_docker_compose_file(directory: str) -> Optional[str]:
    """
    Search for docker-compose.yml beneath a directory.
    """
    for root, _, files in os.walk(directory):
        if "docker-compose.yml" in files:
            return os.path.join(root, "docker-compose.yml")
    return None


def detect_env_file(project_path: str) -> Optional[str]:
    """
    Return the path to a Compose env file if present (.env preferred, fallback to .env/env).
    """
    candidates = [
        os.path.join(project_path, ".env"),
        os.path.join(project_path, ".env", "env"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def compose_cmd(subcmd: str, project_path: str, project_name: Optional[str] = None) -> str:
    """
    Build a docker-compose command string with optional -p and --env-file if present.
    Example: compose_cmd("restart", "/opt/docker/foo", "foo")
    """
    parts: List[str] = [f'cd "{project_path}" && docker-compose']
    if project_name:
        parts += ['-p', f'"{project_name}"']
    env_file = detect_env_file(project_path)
    if env_file:
        parts += ['--env-file', f'"{env_file}"']
    parts += subcmd.split()
    return " ".join(parts)


# ---------------------------
# Business logic
# ---------------------------

def normalize_services_arg(raw: List[str] | None, raw_str: str | None) -> List[str]:
    """
    Accept either:
      - multiple --manipulation SERVICE flags (nargs='*')
      - a single --manipulation-string "svc1 svc2 ..." (space or comma separated)
    """
    if raw:
        return [s for s in raw if s.strip()]
    if raw_str:
        parts = [p.strip() for chunk in raw_str.split(",") for p in chunk.split()]
        return [p for p in parts if p]
    return []


def wait_while_manipulation_running(
    services: List[str],
    waiting_time: int = 600,
    timeout: Optional[int] = None,
) -> None:
    """
    Wait until none of the given services are active anymore.
    Stops waiting if timeout (in seconds) is reached.
    """
    if not services:
        print("No manipulation services provided. Continuing without wait.")
        return

    start = time.time()
    while True:
        any_active = False
        for svc in services:
            res = subprocess.run(f"systemctl is-active --quiet {svc}", shell=True)
            if res.returncode == 0:
                any_active = True
                break

        if any_active:
            elapsed = time.time() - start
            if timeout and elapsed >= timeout:
                print(f"Timeout ({timeout}s) reached while waiting for services. Continuing anyway.")
                break
            print(f"Manipulation service is running. Trying again in {waiting_time} seconds.")
            time.sleep(waiting_time)
        else:
            print("No blocking service is running.")
            break


def get_compose_project_info(container: str) -> Tuple[str, str]:
    """
    Resolve project name and working dir from Docker labels.
    STRICT: Raises RuntimeError if labels are missing/unreadable.
    """
    out_project = print_bash(
        f"docker inspect -f '{{{{ index .Config.Labels \"com.docker.compose.project\" }}}}' {container}"
    )
    out_workdir = print_bash(
        f"docker inspect -f '{{{{ index .Config.Labels \"com.docker.compose.project.working_dir\" }}}}' {container}"
    )

    project = out_project[0].strip() if out_project else ""
    workdir = out_workdir[0].strip() if out_workdir else ""

    if not project:
        raise RuntimeError(f"No compose project label found for container {container}")
    if not workdir:
        raise RuntimeError(f"No compose working_dir label found for container {container}")

    return project, workdir


def main(base_directory: str, manipulation_services: List[str], timeout: Optional[int]) -> int:
    errors = 0
    wait_while_manipulation_running(manipulation_services, waiting_time=600, timeout=timeout)

    unhealthy_container_names = print_bash(
        "docker ps --filter health=unhealthy --format '{{.Names}}'"
    )
    exited_container_names = print_bash(
        "docker ps --filter status=exited --format '{{.Names}}'"
    )
    failed_containers = unhealthy_container_names + exited_container_names

    for container in failed_containers:
        try:
            project, workdir = get_compose_project_info(container)
        except Exception as e:
            print(f"Error reading compose labels for {container}: {e}")
            errors += 1
            continue

        compose_file_path = os.path.join(workdir, "docker-compose.yml")
        if not os.path.isfile(compose_file_path):
            # As STRICT: we only trust labels; if file not there, error out.
            print(f"Error: docker-compose.yml not found at {compose_file_path} for container {container}")
            errors += 1
            continue

        project_path = os.path.dirname(compose_file_path)
        try:
            print("Restarting unhealthy container in:", compose_file_path)
            print_bash(compose_cmd("restart", project_path, project))
        except Exception as e:
            if "port is already allocated" in str(e):
                print("Detected port allocation problem. Executing recovery steps...")
                try:
                    print_bash(compose_cmd("down", project_path))
                    print_bash("systemctl restart docker")
                    print_bash(compose_cmd("up -d", project_path, project))
                except Exception as e2:
                    print("Unhandled exception during recovery:", e2)
                    errors += 1
            else:
                print("Unhandled exception during restart:", e)
                errors += 1

    print("Finished restart procedure.")
    return errors


# ---------------------------
# CLI
# ---------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Restart Docker-Compose configurations with exited or unhealthy containers (STRICT label mode)."
    )
    parser.add_argument(
        "--manipulation",
        metavar="SERVICE",
        nargs="*",
        help="Blocking systemd services to wait for (can be specified multiple times).",
    )
    parser.add_argument(
        "--manipulation-string",
        type=str,
        help='Blocking services as a single string (space- or comma-separated), e.g. "svc1 svc2" or "svc1,svc2".',
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Maximum time in seconds to wait for manipulation services before continuing. (Default 1min)",
    )
    parser.add_argument(
        "base_directory",
        type=str,
        help="(Unused in STRICT mode) Base directory where Docker Compose configurations are located.",
    )
    args = parser.parse_args()
    services = normalize_services_arg(args.manipulation, args.manipulation_string)
    exit(main(args.base_directory, services, args.timeout))
