from __future__ import annotations

from pathlib import Path


def log_path(logs_dir: Path, deploy_type: str, distro: str, suffix: str) -> Path:
    return logs_dir / f"deploy-{deploy_type}-{distro}-{suffix}.log"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="replace")
    path.write_text(existing + text, encoding="utf-8")
