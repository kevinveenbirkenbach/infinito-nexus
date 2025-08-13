#!/usr/bin/env python3

import argparse
import subprocess
import os
import datetime
import sys

def run_ansible_playbook(
    inventory,
    modes,
    limit=None,
    allowed_applications=None,
    password_file=None,
    verbose=0,
    skip_tests=False,
    skip_validation=False,
    skip_build=False,
    cleanup=False,
    logs=False
):
    start_time = datetime.datetime.now()
    print(f"\n▶️ Script started at: {start_time.isoformat()}\n")

    if cleanup:
        cleanup_command = ["make", "clean-keep-logs"] if logs else ["make", "clean"]
        print("\n🧹 Cleaning up project (" + " ".join(cleanup_command) +")...\n")
        subprocess.run(cleanup_command, check=True)
    else:
        print("\n⚠️ Skipping build as requested.\n")

    if not skip_build:
        print("\n🛠️  Building project (make messy-build)...\n")
        subprocess.run(["make", "messy-build"], check=True)
    else:
        print("\n⚠️ Skipping build as requested.\n")

    script_dir = os.path.dirname(os.path.realpath(__file__))
    playbook = os.path.join(os.path.dirname(script_dir), "playbook.yml")

    # Inventory validation step
    if not skip_validation:
        print("\n🔍 Validating inventory before deployment...\n")
        try:
            subprocess.run(
                [sys.executable,
                 os.path.join(script_dir, "validate/inventory.py"),
                 os.path.dirname(inventory)
                ],
                check=True
            )
        except subprocess.CalledProcessError:
            print(
                "\n❌ Inventory validation failed. Deployment aborted.\n",
                file=sys.stderr
            )
            sys.exit(1)
    else:
        print("\n⚠️ Skipping inventory validation as requested.\n")

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
            if not status['in_roles']:
                reasons.append("not defined in roles (infinito)")
            if not status['in_inventory']:
                reasons.append("not found in inventory file")
            print(f"  - {app_id}: " + ", ".join(reasons))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Run the central Ansible deployment script to manage infrastructure, updates, and tests."
    )

    parser.add_argument(
        "inventory",
        help="Path to the inventory file (INI or YAML) containing hosts and variables."
    )
    parser.add_argument(
        "-l", "--limit",
        help="Restrict execution to a specific host or host group from the inventory."
    )
    parser.add_argument(
        "-T", "--host-type",
        choices=["server", "desktop"],
        default="server",
        help="Specify whether the target is a server or a personal computer. Affects role selection and variables."
    )
    parser.add_argument(
        "-r", "--reset", action="store_true",
        help="Reset all Infinito.Nexus files and configurations, and run the entire playbook (not just individual roles)."
    )
    parser.add_argument(
        "-t", "--test", action="store_true",
        help="Run test routines instead of production tasks. Useful for local testing and CI pipelines."
    )
    parser.add_argument(
        "-u", "--update", action="store_true",
        help="Enable the update procedure to bring software and roles up to date."
    )
    parser.add_argument(
        "-b", "--backup", action="store_true",
        help="Perform a full backup of critical data and configurations before the update process."
    )
    parser.add_argument(
        "-c", "--cleanup", action="store_true",
        help="Clean up unused files and outdated configurations after all tasks are complete. Also cleans up the repository before the deployment procedure."
    )
    parser.add_argument(
        "-d", "--debug", action="store_true",
        help="Enable detailed debug output for Ansible and this script."
    )
    parser.add_argument(
        "-p", "--password-file",
        help="Path to the file containing the Vault password. If not provided, prompts for the password interactively."
    )
    parser.add_argument(
        "-s", "--skip-tests", action="store_true",
        help="Skip running 'make test' even if tests are normally enabled."
    )
    parser.add_argument(
        "-V", "--skip-validation", action="store_true",
        help="Skip inventory validation before deployment."
    )
    parser.add_argument(
        "-B", "--skip-build", action="store_true",
        help="Skip running 'make build' before deployment."
    )
    parser.add_argument(
        "-i", "--id", 
        nargs="+",
        default=[],
        dest="id",
        help="List of application_id's for partial deploy. If not set, all application IDs defined in the inventory will be executed."
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Increase verbosity level. Multiple -v flags increase detail (e.g., -vvv for maximum log output)."
    )
    parser.add_argument(
        "--logs", action="store_true",
        help="Keep the CLI logs during cleanup command"
    )

    args = parser.parse_args()
    validate_application_ids(args.inventory, args.id)

    modes = {
        "MODE_RESET": args.reset,
        "MODE_TEST": args.test,
        "MODE_UPDATE": args.update,
        "MODE_BACKUP": args.backup,
        "MODE_CLEANUP": args.cleanup,
        "MODE_LOGS": args.logs,
        "MODE_DEBUG": args.debug,
        "host_type": args.host_type
    }

    run_ansible_playbook(
        inventory=args.inventory,
        modes=modes,
        limit=args.limit,
        allowed_applications=args.id,
        password_file=args.password_file,
        verbose=args.verbose,
        skip_tests=args.skip_tests,
        skip_validation=args.skip_validation,
        skip_build=args.skip_build,
        cleanup=args.cleanup,
        logs=args.logs
    )


if __name__ == "__main__":
    main()
