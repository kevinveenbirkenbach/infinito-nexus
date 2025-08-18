#!/usr/bin/env python3

import os
import re
import subprocess
import sys
import argparse

def extract_domains(config_path):
    """
    Extracts domain names from .conf filenames in the given directory.
    """
    domain_pattern = re.compile(r'^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\.conf$')
    try:
        return [
            fn[:-5]
            for fn in os.listdir(config_path)
            if fn.endswith(".conf") and domain_pattern.match(fn)
        ]
    except FileNotFoundError:
        print(f"Directory {config_path} not found.", file=sys.stderr)
        return None

def run_checkcsp(domains):
    """
    Executes the 'checkcsp' command with the given domains.
    """
    cmd = ["checkcsp", "start", "--short"] + domains
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"'checkcsp' reported issues (exit code {e.returncode})", file=sys.stderr)
        return e.returncode
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

def main():
    parser = argparse.ArgumentParser(
        description="Extract domains from NGINX and run checkcsp against them"
    )
    parser.add_argument(
        "--nginx-config-dir",
        required=True,
        help="Directory containing NGINX .conf files"
    )
    args = parser.parse_args()

    domains = extract_domains(args.nginx_config_dir)
    if domains is None:
        sys.exit(1)

    if not domains:
        print("No domains found to check.")
        sys.exit(0)

    rc = run_checkcsp(domains)
    sys.exit(rc)

if __name__ == "__main__":
    main()
