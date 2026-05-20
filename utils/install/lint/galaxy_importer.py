"""Install galaxy-importer via pip + import-check."""

from __future__ import annotations

import os
import subprocess

from utils.install.pip import detect_python_bin, install_pip_pkg
from utils.install.primitives import log


def _module_importable() -> bool:
    try:
        python_bin = detect_python_bin()
    except RuntimeError:
        return False
    result = subprocess.run(
        [python_bin, "-c", "import galaxy_importer"], capture_output=True, check=False
    )
    return result.returncode == 0


def ensure() -> None:
    if _module_importable():
        return
    log("Missing Python module 'galaxy_importer'. Installing via pip.")
    spec = os.environ.get("GALAXY_IMPORTER_PIP_SPEC", "galaxy-importer")
    install_pip_pkg(spec)
    if not _module_importable():
        raise RuntimeError(
            "Module 'galaxy_importer' is still unimportable after installation."
        )
