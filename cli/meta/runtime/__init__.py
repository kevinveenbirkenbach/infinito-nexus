from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]


def detect_runtime(project_root: Path | None = None) -> str:
    """
    Detect the current execution runtime.

    Returns one of:
      - "act"    : local GitHub Actions emulation (act)
      - "github" : real GitHub Actions runner
      - "dev"    : local development compose stack
      - "host"   : native host execution (default)

    Precedence:
      1) RUNTIME (explicit override)
      2) act (must come before github because act sets GITHUB_ACTIONS=true)
      3) github
      4) dev (marker relative to project root)
      5) host
    """
    # 1) explicit override wins
    v = (os.getenv("RUNTIME") or "").strip()
    if v:
        return v

    # 2) act (must be before GitHub)
    if os.getenv("ACT") == "true" or os.getenv("ACT_RUNNER"):
        return "act"

    # 3) GitHub Actions
    if (
        os.getenv("GITHUB_ACTIONS") == "true"
        or os.getenv("INFINITO_RUNNING_ON_GITHUB") == "true"
    ):
        return "github"

    # 4) local dev compose stack (project-root relative marker)
    root = project_root or PROJECT_ROOT

    if (root / "env.development").exists():
        return "dev"

    # 5) default
    return "host"
