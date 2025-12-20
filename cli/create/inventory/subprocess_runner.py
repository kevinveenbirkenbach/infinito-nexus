from __future__ import annotations

import subprocess
from typing import Dict, List, Optional


def run_subprocess(
    cmd: List[str],
    capture_output: bool = False,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """
    Run a subprocess command and either stream output or capture it.
    Raise SystemExit on non-zero return code.
    """
    if capture_output:
        result = subprocess.run(cmd, text=True, capture_output=True, env=env)
    else:
        result = subprocess.run(cmd, text=True, env=env)

    if result.returncode != 0:
        msg = f"Command failed: {' '.join(str(c) for c in cmd)}\n"
        if capture_output:
            msg += f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n"
        raise SystemExit(msg)

    return result
