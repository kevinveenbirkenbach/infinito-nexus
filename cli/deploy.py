#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Infinito.Nexus deploy CLI

This script is the main entrypoint for running the Ansible playbook with
dynamic MODE_* flags, automatic inventory validation, and optional build/test
steps.
"""

import argparse
import subprocess
import os
import datetime
import sys
import re
from typing import Optional, Dict, Any, List


def run_ansible_playbook(
    inventory: str,
    modes: Dict[str, Any],
    limit: Optional[str] = None,
    allowed_applications: Optional[List[str]] = None,
    password_file: Optional[str] = None,
    verbose: int = 0,
    skip_build: bool = False,
    skip_tests: bool = False,
    logs: bool = False,
    diff: bool = False,
) -> None:
    """Run ansible-playbook with the given parameters and modes."""
    start_time = datetime.datetime.now()
    print(f"\n▶️ Script started at: {start_time.isoformat()}\n")

    # 1) Cleanup phase (MODE_CLEANUP)
    if modes.get("MODE_CLEANUP", False):
        cleanup_command = ["make", "clean-keep-logs"] if logs else ["make", "clean"]
        print(f"\n🧹 Cleaning up project ({' '.join(cleanup_command)})...\n")
        subprocess.run(cleanup_command, check=True)
    else:
        print("\n🧹 Cleanup skipped (MODE_CLEANUP=false or not set)\n")

    # 2) Build phase
    if not skip_build:
        print("\n🛠️  Building project (make messy-build)...\n")
        subprocess.run(["make", "messy-build"], check=True)
    else:
        print("\n🛠️  Build skipped (--skip-build)\n")

    script_dir = os.path.dirname(os.path.realpath(__file__))
    repo_root = os.path.dirname(script_dir)
    playbook = os.path.join(repo_root, "playbook.yml")

    # 3) Inventory validation phase (MODE_ASSERT)
    if modes.get("MODE_ASSERT", None) is False:
        print("\n🔍 Inventory assertion explicitly disabled (MODE_ASSERT=false)\n")
    elif "MODE_ASSERT" not in modes or modes["MODE_ASSERT"] is True:
        print("\n🔍 Validating inventory before deployment...\n")
        try:
            subprocess.run(
                [
                    sys.executable,
                    os.path.join(script_dir, "validate", "inventory.py"),
                    os.path.dirname(inventory),
                ],
                check=True,
            )
        except subprocess.CalledProcessError:
            print(
                "\n[ERROR] Inventory validation failed. Aborting deploy.\n",
                file=sys.stderr,
            )
            sys.exit(1)

    # 4) Test phase
    if not skip_tests:
        print("\n🧪 Running tests (make messy-test)...\n")
        subprocess.run(["make", "messy-test"], check=True)
    else:
        print("\n🧪 Tests skipped (--skip-tests)\n")

    # 5) Build ansible-playbook command
    cmd: List[str] = ["ansible-playbook", "-i", inventory, playbook]

    # --limit / -l
    if limit:
        cmd.extend(["-l", limit])

    # extra var: allowed_applications
    if allowed_applications:
        joined = ",".join(allowed_applications)
        cmd.extend(["-e", f"allowed_applications={joined}"])

    # inject MODE_* variables as extra vars
    for key, value in modes.items():
        val = str(value).lower() if isinstance(value, bool) else str(value)
        cmd.extend(["-e", f"{key}={val}"])

    # vault password handling
    if password_file:
        # If a file is explicitly provided, pass it through
        cmd.extend(["--vault-password-file", password_file])
    # else:
    #   No explicit vault option → ansible will prompt if it needs a password.
    #   This keeps the old behaviour and the CLI help text correct.

    # diff mode
    if diff:
        cmd.append("--diff")

    # MODE_DEBUG=true → always at least -vvv
    if modes.get("MODE_DEBUG", False):
        verbose = max(verbose, 3)

    # verbosity flags
    if verbose:
        cmd.append("-" + "v" * verbose)

    print("\n🚀 Launching Ansible Playbook...\n")
    # Capture output so the real Ansible error is visible before exit
    result = subprocess.run(cmd, text=True, capture_output=True)

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")

    if result.returncode != 0:
        print(
            f"\n[ERROR] ansible-playbook exited with status {result.returncode}\n",
            file=sys.stderr,
        )
        sys.exit(result.returncode)

    end_time = datetime.datetime.now()
    print(f"\n✅ Script ended at: {end_time.isoformat()}\n")

    duration = end_time - start_time
    print(f"⏱️ Total execution time: {duration}\n")


def validate_application_ids(inventory: str, app_ids: List[str]) -> None:
    """Use ValidDeployId helper to ensure all requested IDs are valid."""
    if not app_ids:
        return

    from module_utils.valid_deploy_id import ValidDeployId

    validator = ValidDeployId()
    invalid = validator.validate(inventory, app_ids)
    if invalid:
        print("\n[ERROR] Some application_ids are invalid for this inventory:\n")
        for app_id, status in invalid.items():
            reasons: List[str] = []
            if not status.get("allowed", True):
                reasons.append("not allowed by configuration")
            if not status.get("in_inventory", True):
                reasons.append("not present in inventory")
            print(f"  - {app_id}: " + ", ".join(reasons))
        sys.exit(1)


MODE_LINE_RE = re.compile(
    r"""^\s*(?P<key>[A-Z0-9_]+)\s*:\s*(?P<value>.+?)\s*(?:#\s*(?P<cmt>.*))?\s*$"""
)


def _parse_bool_literal(text: str) -> Optional[bool]:
    """Parse a simple true/false/yes/no/on/off into bool or None."""
    t = text.strip().lower()
    if t in ("true", "yes", "on"):
        return True
    if t in ("false", "no", "off"):
        return False
    return None


def load_modes_from_yaml(modes_yaml_path: str) -> List[Dict[str, Any]]:
    """
    Load MODE_* metadata from a simple key: value file.

    Each non-comment, non-empty line is parsed via MODE_LINE_RE.
    """
    modes: List[Dict[str, Any]] = []
    if not os.path.exists(modes_yaml_path):
        raise FileNotFoundError(f"Modes file not found: {modes_yaml_path}")

    with open(modes_yaml_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            m = MODE_LINE_RE.match(line)
            if not m:
                continue
            key = m.group("key")
            val = m.group("value").strip()
            cmt = (m.group("cmt") or "").strip()

            if not key.startswith("MODE_"):
                continue

            default_bool = _parse_bool_literal(val)
            modes.append(
                {
                    "name": key,
                    "default": default_bool,
                    "help": cmt or f"Toggle {key}",
                }
            )
    return modes


def add_dynamic_mode_args(
    parser: argparse.ArgumentParser, modes_meta: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Add dynamic CLI flags based on MODE_* metadata.

    - MODE_FOO: true  -> --skip-foo (default enabled, flag disables it)
    - MODE_BAR: false -> --bar     (default disabled, flag enables it)
    - MODE_BAZ: null  -> --baz {true,false} (explicit)
    """
    spec: Dict[str, Dict[str, Any]] = {}
    for m in modes_meta:
        name = m["name"]
        default = m["default"]
        desc = m["help"]
        short = name.replace("MODE_", "").lower()

        if default is True:
            opt = f"--skip-{short}"
            dest = f"skip_{short}"
            help_txt = desc or f"Skip/disable {short} (default: enabled)"
            parser.add_argument(opt, action="store_true", help=help_txt, dest=dest)
            spec[name] = {"dest": dest, "default": True, "kind": "bool_true"}
        elif default is False:
            opt = f"--{short}"
            dest = short
            help_txt = desc or f"Enable {short} (default: disabled)"
            parser.add_argument(opt, action="store_true", help=help_txt, dest=dest)
            spec[name] = {"dest": dest, "default": False, "kind": "bool_false"}
        else:
            opt = f"--{short}"
            dest = short
            help_txt = (
                desc
                or f"Set {short} explicitly (true/false). If omitted, keep inventory default."
            )
            parser.add_argument(opt, choices=["true", "false"], help=help_txt, dest=dest)
            spec[name] = {"dest": dest, "default": None, "kind": "explicit"}

    return spec


def build_modes_from_args(
    spec: Dict[str, Dict[str, Any]], args_namespace: argparse.Namespace
) -> Dict[str, Any]:
    """
    Build a MODE_* dict from parsed CLI args and the dynamic spec.
    """
    modes: Dict[str, Any] = {}
    for mode_name, info in spec.items():
        dest = info["dest"]
        kind = info["kind"]
        val = getattr(args_namespace, dest, None)

        if kind == "bool_true":
            # default True, flag means "skip" → False
            modes[mode_name] = False if val else True
        elif kind == "bool_false":
            # default False, flag enables → True
            modes[mode_name] = True if val else False
        else:  # explicit
            if val is not None:
                modes[mode_name] = True if val == "true" else False
    return modes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy the Infinito.Nexus stack via ansible-playbook."
    )

    parser.add_argument(
        "inventory",
        help="Path to the inventory file (INI or YAML) containing hosts and variables.",
    )
    parser.add_argument(
        "-l",
        "--limit",
        help="Restrict execution to a specific host or host group from the inventory.",
    )
    parser.add_argument(
        "-T",
        "--host-type",
        choices=["server", "desktop"],
        default="server",
        help=(
            "Specify whether the target is a server or a personal computer. "
            "Affects role selection and variables."
        ),
    )
    parser.add_argument(
        "-p",
        "--password-file",
        help=(
            "Path to the file containing the Vault password. "
            "If not provided, ansible-vault will prompt interactively."
        ),
    )
    parser.add_argument(
        "-B",
        "--skip-build",
        action="store_true",
        help="Skip running 'make messy-build' before deployment.",
    )
    parser.add_argument(
        "-t",
        "--skip-tests",
        action="store_true",
        help="Skip running 'make messy-test' before deployment.",
    )
    parser.add_argument(
        "-i",
        "--id",
        nargs="+",
        default=[],
        dest="id",
        help=(
            "List of application_id's for partial deploy. "
            "If not set, all application IDs defined in the inventory will be executed."
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help=(
            "Increase verbosity level. Multiple -v flags increase detail "
            "(e.g., -vvv for maximum log output)."
        ),
    )
    parser.add_argument(
        "--logs",
        action="store_true",
        help="Keep the CLI logs during cleanup command.",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Pass --diff to ansible-playbook to show configuration changes.",
    )

    script_dir = os.path.dirname(os.path.realpath(__file__))
    repo_root = os.path.dirname(script_dir)
    modes_yaml_path = os.path.join(repo_root, "group_vars", "all", "01_modes.yml")
    modes_meta = load_modes_from_yaml(modes_yaml_path)
    modes_spec = add_dynamic_mode_args(parser, modes_meta)

    args = parser.parse_args()
    validate_application_ids(args.inventory, args.id)

    modes = build_modes_from_args(modes_spec, args)
    modes["MODE_LOGS"] = args.logs
    modes["host_type"] = args.host_type

    run_ansible_playbook(
        inventory=args.inventory,
        modes=modes,
        limit=args.limit,
        allowed_applications=args.id,
        password_file=args.password_file,
        verbose=args.verbose,
        skip_build=args.skip_build,
        skip_tests=args.skip_tests,
        logs=args.logs,
        diff=args.diff,
    )


if __name__ == "__main__":
    main()
