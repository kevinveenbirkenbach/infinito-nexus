from __future__ import annotations

import os


def _resolve_repo_root() -> str:
    """
    Resolve repository root based on this file location.

    Current file: <repo>/cli/deploy/dedicated/paths.py
    """
    here = os.path.realpath(__file__)
    dedicated_dir = os.path.dirname(here)  # .../cli/deploy/dedicated
    deploy_dir = os.path.dirname(dedicated_dir)  # .../cli/deploy
    cli_root = os.path.dirname(deploy_dir)  # .../cli
    repo_root = os.path.dirname(cli_root)  # .../<repo-root>
    return repo_root


REPO_ROOT: str = _resolve_repo_root()
CLI_ROOT: str = os.path.join(REPO_ROOT, "cli")
PLAYBOOK_PATH: str = os.path.join(REPO_ROOT, "playbook.yml")
MODES_FILE: str = os.path.join(REPO_ROOT, "group_vars", "all", "01_modes.yml")
INVENTORY_VALIDATOR_PATH: str = os.path.join(
    REPO_ROOT, "cli", "validate", "inventory", "__main__.py"
)
