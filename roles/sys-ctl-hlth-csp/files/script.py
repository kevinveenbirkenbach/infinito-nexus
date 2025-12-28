#!/usr/bin/env python3

import os
import re
import subprocess
import sys
import argparse


def extract_domains(config_path: str) -> list[str] | None:
    """
    Extracts domain names from .conf filenames in the given directory.
    """
    domain_pattern = re.compile(r"^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\.conf$")
    try:
        return [
            fn[:-5]
            for fn in os.listdir(config_path)
            if fn.endswith(".conf") and domain_pattern.match(fn)
        ]
    except FileNotFoundError:
        print(f"Directory {config_path} not found.", file=sys.stderr)
        return None


def build_docker_cmd(
    image: str,
    domains: list[str],
    short_mode: bool,
    ignore_network_blocks_from: list[str],
) -> list[str]:
    """
    Build docker run command that forwards args to the container ENTRYPOINT.
    """
    cmd = ["docker", "run", "--rm", image]

    if short_mode:
        cmd.append("--short")

    if ignore_network_blocks_from:
        cmd.append("--ignore-network-blocks-from")
        cmd.extend(ignore_network_blocks_from)
        cmd.append("--")

    cmd.extend(domains)
    return cmd


def run_checker(
    image: str,
    domains: list[str],
    short_mode: bool,
    ignore_network_blocks_from: list[str],
    always_pull: bool,
) -> int:
    """
    Runs the CSP checker container and returns its exit code.
    """
    if always_pull:
        # best-effort pull; if it fails, continue with local image
        subprocess.run(["docker", "pull", image], check=False)

    cmd = build_docker_cmd(image, domains, short_mode, ignore_network_blocks_from)
    try:
        result = subprocess.run(cmd, check=False)
        return int(result.returncode)
    except FileNotFoundError:
        print("docker not found. Please install Docker.", file=sys.stderr)
        return 127
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract domains from NGINX and run CSP checker (Docker) against them"
    )
    parser.add_argument(
        "--nginx-config-dir",
        required=True,
        help="Directory containing NGINX .conf files",
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Docker image to run (e.g. ghcr.io/kevinveenbirkenbach/csp-checker:latest)",
    )
    parser.add_argument(
        "--always-pull",
        action="store_true",
        help="Pull the docker image before running (best-effort).",
    )
    parser.add_argument(
        "--short",
        action="store_true",
        help="Enable short mode (one example per policy/type).",
    )
    parser.add_argument(
        "--ignore-network-blocks-from",
        nargs="*",
        default=[],
        help="Optional: domains whose network block failures should be ignored",
    )

    args = parser.parse_args()

    domains = extract_domains(args.nginx_config_dir)
    if domains is None:
        sys.exit(1)

    if not domains:
        print("No domains found to check.")
        sys.exit(0)

    rc = run_checker(
        image=args.image,
        domains=domains,
        short_mode=bool(args.short),
        ignore_network_blocks_from=list(args.ignore_network_blocks_from or []),
        always_pull=bool(args.always_pull),
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
