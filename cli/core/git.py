from __future__ import annotations

import subprocess


def git_clean_repo() -> None:
    subprocess.run(["git", "clean", "-Xfd"], check=True)
