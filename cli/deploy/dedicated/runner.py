from __future__ import annotations

import datetime
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

from .proc import run, run_make


def run_ansible_playbook(
    *,
    repo_root: str,
    cli_root: str,
    playbook_path: str,
    inventory_validator_path: str,
    inventory: str,
    modes: Dict[str, Any],
    limit: Optional[str] = None,
    allowed_applications: Optional[List[str]] = None,
    password_file: Optional[str] = None,
    verbose: int = 0,
    skip_build: bool = False,
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
        print("\n🧹 Cleaning up...\n", flush=True)
        run_make(repo_root, "clean")
    else:
        print("\n🧹 Cleanup skipped (MODE_CLEANUP not set or False)\n")

    # ---------------------------------------------------------
    # 2) Build Phase
    # ---------------------------------------------------------
    if not skip_build:
        print("\n🛠️  Running project build (make setup)...\n")
        run_make(repo_root, "setup")
    else:
        print("\n🛠️  Build skipped (--skip-build)\n")

    # ---------------------------------------------------------
    # 3) Inventory Validation Phase
    # ---------------------------------------------------------
    if modes.get("MODE_ASSERT", None) is False:
        print("\n🔍 Inventory assertion explicitly disabled (MODE_ASSERT=false)\n")
    else:
        print("\n🔍 Validating inventory before deployment...\n")
        try:
            run(
                [sys.executable, inventory_validator_path, os.path.dirname(inventory)],
                cwd=repo_root,
                check=True,
            )
        except subprocess.CalledProcessError:
            print(
                "\n[ERROR] Inventory validation failed. Aborting deployment.\n",
                file=sys.stderr,
            )
            sys.exit(1)

    # ---------------------------------------------------------
    # 5) Build ansible-playbook command
    # ---------------------------------------------------------
    cmd: List[str] = ["ansible-playbook", "-i", inventory, playbook_path]

    if limit:
        cmd.extend(["-l", limit])

    if allowed_applications:
        joined = ",".join(allowed_applications)
        cmd.extend(["-e", f"allowed_applications={joined}"])

    for key, value in modes.items():
        val = str(value).lower() if isinstance(value, bool) else str(value)
        cmd.extend(["-e", f"{key}={val}"])

    if password_file:
        cmd.extend(["--vault-password-file", password_file])

    if diff:
        cmd.append("--diff")

    if modes.get("MODE_DEBUG", False):
        verbose = max(verbose, 3)

    if verbose:
        cmd.append("-" + "v" * verbose)

    print("\n🚀 Launching Ansible Playbook...\n")
    result = subprocess.run(cmd, cwd=repo_root)

    if result.returncode != 0:
        print(
            f"\n[ERROR] ansible-playbook exited with status {result.returncode}\n",
            file=sys.stderr,
        )
        sys.exit(result.returncode)

    end_time = datetime.datetime.now()
    print(f"\n✅ Script ended at: {end_time.isoformat()}\n")
    print(f"⏱️ Total execution time: {end_time - start_time}\n")
