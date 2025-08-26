#!/usr/bin/env python3
"""
Restart Docker-Compose configurations with exited or unhealthy containers.
This version receives the *manipulation services* via argparse (no Jinja).
"""
import subprocess
import time
import os
import argparse
from typing import List


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
    output = bash(command)
    if output:
        print(list_to_string(output))
    return output


def find_docker_compose_file(directory: str) -> str | None:
    for root, _, files in os.walk(directory):
        if "docker-compose.yml" in files:
            return os.path.join(root, "docker-compose.yml")
    return None


def detect_env_file(project_path: str) -> str | None:
    """
    Return the path to a Compose env file if present (.env preferred, fallback to env).
    """
    candidates = [os.path.join(project_path, ".env"), os.path.join(project_path, ".env", "env")]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def compose_cmd(subcmd: str, project_path: str, project_name: str | None = None) -> str:
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


def normalize_services_arg(raw: List[str] | None, raw_str: str | None) -> List[str]:
    """
    Accept either:
      - multiple --manipulation SERVICE flags (nargs='*')
      - a single --manipulation-string "svc1 svc2 ..." (space or comma separated)
    """
    if raw:
        return [s for s in raw if s.strip()]
    if raw_str:
        # split on comma or whitespace
        parts = [p.strip() for chunk in raw_str.split(",") for p in chunk.split()]
        return [p for p in parts if p]
    return []


def wait_while_manipulation_running(
    services: List[str],
    waiting_time: int = 600,
    timeout: int | None = None,
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
            # Check timeout
            elapsed = time.time() - start
            if timeout and elapsed >= timeout:
                print(f"Timeout ({timeout}s) reached while waiting for services. Continuing anyway.")
                break
            print(f"Manipulation service is running. Trying again in {waiting_time} seconds.")
            time.sleep(waiting_time)
        else:
            print("No blocking service is running.")
            break


def main(base_directory: str, manipulation_services: List[str], timeout: int | None) -> int:
    errors = 0
    wait_while_manipulation_running(manipulation_services, waiting_time=600, timeout=timeout)

    unhealthy_container_names = print_bash(
        "docker ps --filter health=unhealthy --format '{{.Names}}'"
    )
    exited_container_names = print_bash(
        "docker ps --filter status=exited --format '{{.Names}}'"
    )
    failed_containers = unhealthy_container_names + exited_container_names

    unfiltered_failed_docker_compose_repositories = [
        container.split("-")[0] for container in failed_containers
    ]
    filtered_failed_docker_compose_repositories = list(
        dict.fromkeys(unfiltered_failed_docker_compose_repositories)
    )

    for repo in filtered_failed_docker_compose_repositories:
        compose_file_path = find_docker_compose_file(os.path.join(base_directory, repo))

        if compose_file_path:
            print("Restarting unhealthy container in:", compose_file_path)
            project_path = os.path.dirname(compose_file_path)
            try:
                # restart with optional --env-file and -p
                print_bash(compose_cmd("restart", project_path, repo))
            except Exception as e:
                if "port is already allocated" in str(e):
                    print("Detected port allocation problem. Executing recovery steps...")
                    # down (no -p needed), then engine restart, then up -d with -p
                    print_bash(compose_cmd("down", project_path))
                    print_bash("systemctl restart docker")
                    print_bash(compose_cmd("up -d", project_path, repo))
                else:
                    print("Unhandled exception during restart:", e)
                    errors += 1
        else:
            print("Error: Docker Compose file not found for:", repo)
            errors += 1

    print("Finished restart procedure.")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Restart Docker-Compose configurations with exited or unhealthy containers."
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
        help="Maximum time in seconds to wait for manipulation services before continuing.(Default 1min)",
    )
    parser.add_argument(
        "base_directory",
        type=str,
        help="Base directory where Docker Compose configurations are located.",
    )
    args = parser.parse_args()
    services = normalize_services_arg(args.manipulation, args.manipulation_string)
    exit(main(args.base_directory, services, args.timeout))
