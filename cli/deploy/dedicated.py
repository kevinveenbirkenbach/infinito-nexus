    #!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Infinito.Nexus Deploy CLI

This script is the main entrypoint for running the Ansible playbook with
dynamic MODE_* flags, automatic inventory validation, and optional build/test
phases. It supports partial deployments, dynamic MODE flag generation,
inventory validation, and structured execution flow.
"""

import argparse
import subprocess
import os
import datetime
import sys
import re
from typing import Optional, Dict, Any, List


# --------------------------------------------------------------------------------------
# Path resolution
# --------------------------------------------------------------------------------------

# Current file: .../cli/deploy/deploy.py
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))        # → cli/deploy
CLI_ROOT   = os.path.dirname(SCRIPT_DIR)                        # → cli
REPO_ROOT  = os.path.dirname(CLI_ROOT)                          # → project root


# --------------------------------------------------------------------------------------
# Main execution logic
# --------------------------------------------------------------------------------------

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
    """Run ansible-playbook with the given parameters and execution modes."""
    start_time = datetime.datetime.now()
    print(f"\n▶️ Script started at: {start_time.isoformat()}\n")

    # ---------------------------------------------------------
    # 1) Cleanup Phase
    # ---------------------------------------------------------
    if modes.get("MODE_CLEANUP", False):
        cleanup_cmd = ["make", "clean-keep-logs"] if logs else ["make", "clean"]
        print(f"\n🧹 Running cleanup ({' '.join(cleanup_cmd)})...\n")
        subprocess.run(cleanup_cmd, check=True)
    else:
        print("\n🧹 Cleanup skipped (MODE_CLEANUP not set or False)\n")

    # ---------------------------------------------------------
    # 2) Build Phase
    # ---------------------------------------------------------
    if not skip_build:
        print("\n🛠️  Running project build (make messy-build)...\n")
        subprocess.run(["make", "messy-build"], check=True)
    else:
        print("\n🛠️  Build skipped (--skip-build)\n")

    # The Ansible playbook is located in the repo root
    playbook_path = os.path.join(REPO_ROOT, "playbook.yml")

    # ---------------------------------------------------------
    # 3) Inventory Validation Phase
    # ---------------------------------------------------------
    if modes.get("MODE_ASSERT", None) is False:
        print("\n🔍 Inventory assertion explicitly disabled (MODE_ASSERT=false)\n")
    else:
        print("\n🔍 Validating inventory before deployment...\n")
        validator_path = os.path.join(CLI_ROOT, "validate", "inventory.py")
        try:
            subprocess.run(
                [sys.executable, validator_path, os.path.dirname(inventory)],
                check=True,
            )
        except subprocess.CalledProcessError:
            print(
                "\n[ERROR] Inventory validation failed. Aborting deployment.\n",
                file=sys.stderr,
            )
            sys.exit(1)

    # ---------------------------------------------------------
    # 4) Test Phase
    # ---------------------------------------------------------
    if not skip_tests:
        print("\n🧪 Running tests (make messy-test)...\n")
        subprocess.run(["make", "messy-test"], check=True)
    else:
        print("\n🧪 Tests skipped (--skip-tests)\n")

    # ---------------------------------------------------------
    # 5) Build ansible-playbook command
    # ---------------------------------------------------------
    cmd: List[str] = ["ansible-playbook", "-i", inventory, playbook_path]

    # Limit hosts
    if limit:
        cmd.extend(["-l", limit])

    # Allowed applications (partial deployment)
    if allowed_applications:
        joined = ",".join(allowed_applications)
        cmd.extend(["-e", f"allowed_applications={joined}"])

    # MODE_* flags
    for key, value in modes.items():
        val = str(value).lower() if isinstance(value, bool) else str(value)
        cmd.extend(["-e", f"{key}={val}"])

    # Vault password file
    if password_file:
        cmd.extend(["--vault-password-file", password_file])

    # Enable diff mode
    if diff:
        cmd.append("--diff")

    # MODE_DEBUG → enforce high verbosity
    if modes.get("MODE_DEBUG", False):
        verbose = max(verbose, 3)

    # Verbosity flags
    if verbose:
        cmd.append("-" + "v" * verbose)

    print("\n🚀 Launching Ansible Playbook...\n")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(
            f"\n[ERROR] ansible-playbook exited with status {result.returncode}\n",
            file=sys.stderr,
        )
        sys.exit(result.returncode)

    end_time = datetime.datetime.now()

    print(f"\n✅ Script ended at: {end_time.isoformat()}\n")
    print(f"⏱️ Total execution time: {end_time - start_time}\n")


# --------------------------------------------------------------------------------------
# Application ID validation
# --------------------------------------------------------------------------------------

def validate_application_ids(inventory: str, app_ids: List[str]) -> None:
    """Validate requested application IDs using ValidDeployId."""
    if not app_ids:
        return

    from module_utils.valid_deploy_id import ValidDeployId

    validator = ValidDeployId()
    invalid = validator.validate(inventory, app_ids)

    if invalid:
        print("\n[ERROR] Some application_ids are invalid for this inventory:\n")
        for app_id, status in invalid.items():
            reasons = []
            if not status.get("allowed", True):
                reasons.append("not allowed by configuration")
            if not status.get("in_inventory", True):
                reasons.append("not present in inventory")
            print(f"  - {app_id}: {', '.join(reasons)}")
        sys.exit(1)


# --------------------------------------------------------------------------------------
# MODE_* parsing logic
# --------------------------------------------------------------------------------------

MODE_LINE_RE = re.compile(
    r"""^\s*(?P<key>[A-Z0-9_]+)\s*:\s*(?P<value>.+?)\s*(?:#\s*(?P<cmt>.*))?\s*$"""
)


def _parse_bool_literal(text: str) -> Optional[bool]:
    """Convert simple true/false/yes/no/on/off into boolean."""
    t = text.strip().lower()
    if t in ("true", "yes", "on"):
        return True
    if t in ("false", "no", "off"):
        return False
    return None


def load_modes_from_yaml(modes_yaml_path: str) -> List[Dict[str, Any]]:
    """Load MODE_* definitions from YAML-like key/value file."""
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


# --------------------------------------------------------------------------------------
# Dynamic argparse mode injection
# --------------------------------------------------------------------------------------

def add_dynamic_mode_args(
    parser: argparse.ArgumentParser, modes_meta: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Add command-line arguments dynamically based on MODE_* metadata.
    """

    spec: Dict[str, Dict[str, Any]] = {}

    for m in modes_meta:
        name = m["name"]
        default = m["default"]
        desc = m["help"]
        short = name.replace("MODE_", "").lower()

        if default is True:
            # MODE_FOO: true  → --skip-foo disables it
            opt = f"--skip-{short}"
            dest = f"skip_{short}"
            parser.add_argument(opt, action="store_true", dest=dest, help=desc)
            spec[name] = {"dest": dest, "default": True, "kind": "bool_true"}

        elif default is False:
            # MODE_BAR: false → --bar enables it
            opt = f"--{short}"
            dest = short
            parser.add_argument(opt, action="store_true", dest=dest, help=desc)
            spec[name] = {"dest": dest, "default": False, "kind": "bool_false"}

        else:
            # Explicit: MODE_XYZ: null → --xyz true|false
            opt = f"--{short}"
            dest = short
            parser.add_argument(opt, choices=["true", "false"], dest=dest, help=desc)
            spec[name] = {"dest": dest, "default": None, "kind": "explicit"}

    return spec


def build_modes_from_args(
    spec: Dict[str, Dict[str, Any]], args_namespace: argparse.Namespace
) -> Dict[str, Any]:
    """Resolve CLI arguments into a MODE_* dictionary."""
    modes: Dict[str, Any] = {}

    for mode_name, info in spec.items():
        dest = info["dest"]
        kind = info["kind"]
        value = getattr(args_namespace, dest, None)

        if kind == "bool_true":
            modes[mode_name] = False if value else True

        elif kind == "bool_false":
            modes[mode_name] = True if value else False

        else:  # explicit
            if value is not None:
                modes[mode_name] = (value == "true")

    return modes


# --------------------------------------------------------------------------------------
# Main entrypoint
# --------------------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy the Infinito.Nexus stack using ansible-playbook."
    )

    # Standard arguments
    parser.add_argument("inventory", help="Path to the inventory file.")
    parser.add_argument("-l", "--limit", help="Limit execution to certain hosts or groups.")
    parser.add_argument(
        "-T", "--host-type", choices=["server", "desktop"], default="server",
        help="Specify target type: server or desktop."
    )
    parser.add_argument(
        "-p", "--password-file",
        help="Vault password file for encrypted variables."
    )
    parser.add_argument("-B", "--skip-build", action="store_true", help="Skip build phase.")
    parser.add_argument("-t", "--skip-tests", action="store_true", help="Skip test phase.")
    parser.add_argument(
        "-i", "--id", nargs="+", default=[], dest="id",
        help="List of application_ids for partial deployment."
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Increase verbosity (e.g. -vvv)."
    )
    parser.add_argument("--logs", action="store_true", help="Keep logs during cleanup.")
    parser.add_argument("--diff", action="store_true", help="Enable Ansible diff mode.")

    # Dynamic MODE_* parsing
    modes_yaml_path = os.path.join(REPO_ROOT, "group_vars", "all", "01_modes.yml")
    modes_meta = load_modes_from_yaml(modes_yaml_path)
    modes_spec = add_dynamic_mode_args(parser, modes_meta)

    args = parser.parse_args()

    # Validate application IDs
    validate_application_ids(args.inventory, args.id)

    # Build final mode map
    modes = build_modes_from_args(modes_spec, args)
    modes["MODE_LOGS"] = args.logs
    modes["host_type"] = args.host_type

    # Run playbook
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
