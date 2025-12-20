from __future__ import annotations

import sys
from typing import List


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
        if not status.get("allowed", True):
            reasons.append("not allowed by configuration")
        if not status.get("in_inventory", True):
            reasons.append("not present in inventory")
        print(f"  - {app_id}: {', '.join(reasons)}")

    sys.exit(1)
