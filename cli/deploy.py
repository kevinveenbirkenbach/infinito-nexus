#!/usr/bin/env python3

import argparse
import subprocess
import os
import datetime
import sys
import re
from typing import Optional, Dict, Any, List


def run_ansible_playbook(
    inventory,
    modes,
    limit=None,
    allowed_applications=None,
    password_file=None,
    verbose=0,
    skip_build=False,
    skip_tests=False,
    logs=False,
    diff=False,
):
    start_time = datetime.datetime.now()
    print(f"\n▶️ Script started at: {start_time.isoformat()}\n")

    # Cleanup is now handled via MODE_CLEANUP
    if modes.get("MODE_CLEANUP", False):
        cleanup_command = ["make", "clean-keep-logs"] if logs else ["make", "clean"]
        print("\n🧹 Cleaning up project (" + " ".join(cleanup_command) + ")...\n")
        subprocess.run(cleanup_command, check=True)
    else:
        print("\n⚠️ Skipping cleanup as requested.\n")

    if not skip_build:
        print("\n🛠️  Building project (make messy-build)...\n")
        subprocess.run(["make", "messy-build"], check=True)
    else:
        print("\n⚠️ Skipping build as requested.\n")

    script_dir = os.path.dirname(os.path.realpath(__file__))
    playbook = os.path.join(os.path.dirname(script_dir), "playbook.yml")

    # Inventory validation is controlled via MODE_ASSERT
    if modes.get("MODE_ASSERT", None) is False:
        print("\n⚠️ Skipping inventory validation as requested.\n")
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
            print("\n❌ Inventory validation failed. Deployment aborted.\n", file=sys.stderr)
            sys.exit(1)
            
    if not skip_tests:
        print("\n🧪 Running tests (make messy-test)...\n")
        subprocess.run(["make", "messy-test"], check=True)

    # Build ansible-playbook command
    cmd = ["ansible-playbook", "-i", inventory, playbook]

    if limit:
        cmd.extend(["--limit", limit])

    if allowed_applications:
        joined = ",".join(allowed_applications)
        cmd.extend(["-e", f"allowed_applications={joined}"])

    for key, value in modes.items():
        val = str(value).lower() if isinstance(value, bool) else str(value)
        cmd.extend(["-e", f"{key}={val}"])

    if password_file:
        cmd.extend(["--vault-password-file", password_file])
    else:
        cmd.extend(["--ask-vault-pass"])

    if diff:
        cmd.append("--diff") 

    if verbose:
        cmd.append("-" + "v" * verbose)

    print("\n🚀 Launching Ansible Playbook...\n")
    subprocess.run(cmd, check=True)

    end_time = datetime.datetime.now()
    print(f"\n✅ Script ended at: {end_time.isoformat()}\n")

    duration = end_time - start_time
    print(f"⏱️ Total execution time: {duration}\n")


def validate_application_ids(inventory, app_ids):
    """
    Abort the script if any application IDs are invalid, with detailed reasons.
    """
    from module_utils.valid_deploy_id import ValidDeployId

    validator = ValidDeployId()
    invalid = validator.validate(inventory, app_ids)
    if invalid:
        print("\n❌ Detected invalid application_id(s):\n")
        for app_id, status in invalid.items():
            reasons = []
            if not status["in_roles"]:
                reasons.append("not defined in roles (infinito)")
            if not status["in_inventory"]:
                reasons.append("not found in inventory file")
            print(f"  - {app_id}: " + ", ".join(reasons))
        sys.exit(1)


MODE_LINE_RE = re.compile(
    r"""^\s*(?P<key>[A-Z0-9_]+)\s*:\s*(?P<value>.+?)\s*(?:#\s*(?P<cmt>.*))?\s*$"""
)


def _parse_bool_literal(text: str) -> Optional[bool]:
    t = text.strip().lower()
    if t in ("true", "yes", "on"):
        return True
    if t in ("false", "no", "off"):
        return False
    return None


def load_modes_from_yaml(modes_yaml_path: str) -> List[Dict[str, Any]]:
    """
    Parse group_vars/all/01_modes.yml line-by-line to recover:
      - name (e.g., MODE_TEST)
      - default (True/False/None if templated/unknown)
      - help (from trailing # comment, if present)
    """
    modes = []
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
    Add argparse options based on modes metadata.
    Returns a dict mapping mode name -> { 'dest': <argparse_dest>, 'default': <bool/None>, 'kind': 'bool_true'|'bool_false'|'explicit' }.
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
            help_txt = desc or f"Set {short} explicitly (true/false). If omitted, keep inventory default."
            parser.add_argument(opt, choices=["true", "false"], help=help_txt, dest=dest)
            spec[name] = {"dest": dest, "default": None, "kind": "explicit"}

    return spec


def build_modes_from_args(
    spec: Dict[str, Dict[str, Any]], args_namespace: argparse.Namespace
) -> Dict[str, Any]:
    """
    Using the argparse results and the spec, compute the `modes` dict to pass to Ansible.
    """
    modes: Dict[str, Any] = {}
    for mode_name, info in spec.items():
        dest = info["dest"]
        kind = info["kind"]
        val = getattr(args_namespace, dest, None)

        if kind == "bool_true":
            modes[mode_name] = False if val else True
        elif kind == "bool_false":
            modes[mode_name] = True if val else False
        else:
            if val is not None:
                modes[mode_name] = True if val == "true" else False
    return modes


def main():
    parser = argparse.ArgumentParser(
        description="Run the central Ansible deployment script to manage infrastructure, updates, and tests."
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
        help="Specify whether the target is a server or a personal computer. Affects role selection and variables.",
    )
    parser.add_argument(
        "-p",
        "--password-file",
        help="Path to the file containing the Vault password. If not provided, prompts for the password interactively.",
    )
    parser.add_argument(
        "-B",
        "--skip-build",
        action="store_true",
        help="Skip running 'make build' before deployment.",
    )
    parser.add_argument(
        "-t",
        "--skip-tests",
        action="store_true",
        help="Skip running 'make messy-tests' before deployment.",
    )
    parser.add_argument(
        "-i",
        "--id",
        nargs="+",
        default=[],
        dest="id",
        help="List of application_id's for partial deploy. If not set, all application IDs defined in the inventory will be executed.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity level. Multiple -v flags increase detail (e.g., -vvv for maximum log output).",
    )
    parser.add_argument(
        "--logs",
        action="store_true",
        help="Keep the CLI logs during cleanup command",
    )
    
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Pass --diff to ansible-playbook to show configuration changes.",
    )

    # ---- Dynamically add mode flags from group_vars/all/01_modes.yml ----
    script_dir = os.path.dirname(os.path.realpath(__file__))
    repo_root = os.path.dirname(script_dir)
    modes_yaml_path = os.path.join(repo_root, "group_vars", "all", "01_modes.yml")
    modes_meta = load_modes_from_yaml(modes_yaml_path)
    modes_spec = add_dynamic_mode_args(parser, modes_meta)

    args = parser.parse_args()
    validate_application_ids(args.inventory, args.id)

    # Build modes from dynamic args
    modes = build_modes_from_args(modes_spec, args)

    # Additional non-dynamic flags
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
