#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path when executing this file directly:
#   python3 cli/__main__.py ...
#
# Without this, sys.path[0] points to "<root>/cli", and importing "cli.*"
# may accidentally resolve to an installed package from site-packages.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cli.core.app import main  # noqa: E402


if __name__ == "__main__":
    main()
