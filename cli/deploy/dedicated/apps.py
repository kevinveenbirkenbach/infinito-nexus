from __future__ import annotations

import sys
from typing import List


def _dump_inventory_full(inventory: str) -> None:
    """
    Print the full inventory file content (raw) to simplify CI debugging.
    """
    import os

    print("\n[DEBUG] Full inventory dump:")
    print(f"[DEBUG] inventory path: {inventory}")

    if not os.path.exists(inventory):
        print("[DEBUG] inventory file does not exist")
        return

    try:
        with open(inventory, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        print("\n===== BEGIN INVENTORY FILE =====")
        print(content.rstrip("\n"))
        print("===== END INVENTORY FILE =====\n")
    except Exception as exc:
        print(f"[DEBUG] failed to read inventory: {exc}")


def validate_application_ids(inventory: str, app_ids: List[str]) -> None:
    """Validate requested application IDs using ValidDeployId."""
    if not app_ids:
        return

    from module_utils.valid_deploy_id import ValidDeployId

    validator = ValidDeployId()
    invalid = validator.validate(inventory, app_ids)

    if not invalid:
        return

    print("\n[ERROR] Some application_ids are invalid for this inventory:\n")
    for app_id, status in invalid.items():
        reasons = []
        if not status.get("in_roles", True):
            reasons.append("not defined as a role")
        if not status.get("in_inventory", True):
            reasons.append("not present in inventory")
        print(f"  - {app_id}: {', '.join(reasons)}")

    _dump_inventory_full(inventory)
    sys.exit(1)
