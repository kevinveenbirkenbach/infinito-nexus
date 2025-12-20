from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .subprocess_runner import run_subprocess
from .yaml_io import load_yaml


def generate_dynamic_inventory(
    host: str,
    roles_dir: Path,
    categories_file: Path,
    tmp_inventory: Path,
    project_root: Path,
    env: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Generate a dynamic inventory by executing the generator as a module:
        python -m cli.build.inventory.full ...

    This avoids fragile file path construction and fixes 'cli/cli/...' issues.
    """
    cmd = [
        sys.executable,
        "-m",
        "cli.build.inventory.full",
        "--host",
        host,
        "--format",
        "yaml",
        "--inventory-style",
        "group",
        "-c",
        str(categories_file),
        "-r",
        str(roles_dir),
        "-o",
        str(tmp_inventory),
    ]
    run_subprocess(cmd, capture_output=False, env=env)
    data = load_yaml(tmp_inventory)
    tmp_inventory.unlink(missing_ok=True)
    return data
