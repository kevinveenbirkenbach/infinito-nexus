from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional

from .subprocess_runner import run_subprocess


def resolve_role_path(
    application_id: str,
    roles_dir: Path,
    project_root: Path,
    env: Optional[Dict[str, str]],
) -> Optional[Path]:
    """
    Resolve role path by calling:
      python -m cli.meta.applications.role_name <app_id> -r <roles_dir>

    The helper may print:
      - bare folder name (e.g. web-app-nextcloud)
      - relative path (e.g. roles/web-app-nextcloud)
      - absolute path
    """
    cmd = [
        sys.executable,
        "-m",
        "cli.meta.applications.role_name",
        application_id,
        "-r",
        str(roles_dir),
    ]
    result = run_subprocess(cmd, capture_output=True, env=env)
    raw = (result.stdout or "").strip()

    if not raw:
        return None

    printed = Path(raw)

    if printed.is_absolute():
        role_path = printed
    else:
        cand1 = roles_dir / printed
        if cand1.exists():
            role_path = cand1
        else:
            cand2 = project_root / printed
            if cand2.exists():
                role_path = cand2
            else:
                return None

    return role_path if role_path.exists() else None
