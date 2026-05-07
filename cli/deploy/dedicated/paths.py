from __future__ import annotations

import os
from pathlib import Path


def _resolve_repo_root() -> str:
    """
    Resolve repository root based on this file location.

    Current file: <repo>/cli/deploy/dedicated/paths.py
    """
    here = os.path.realpath(__file__)
    dedicated_dir = str(Path(here).parent)  # .../cli/deploy/dedicated
    deploy_dir = str(Path(dedicated_dir).parent)  # .../cli/deploy
    cli_root = str(Path(deploy_dir).parent)  # .../cli
    return str(Path(cli_root).parent)  # .../<repo-root>


PROJECT_ROOT: str = _resolve_repo_root()
CLI_ROOT: str = str(Path(PROJECT_ROOT) / "cli")
PLAYBOOK_PATH: str = str(Path(PROJECT_ROOT) / "playbook.yml")
MODES_FILE: str = str(Path(PROJECT_ROOT) / "group_vars" / "all" / "01_modes.yml")
INVENTORY_VALIDATOR_PATH: str = str(
    Path(PROJECT_ROOT) / "cli" / "validate" / "inventory" / "__main__.py"
)
