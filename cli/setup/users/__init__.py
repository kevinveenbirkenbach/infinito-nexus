from __future__ import annotations

import sys
from pathlib import Path
import importlib

def _import_main():
    # When executed as a script, we have no package context.
    if __package__ in (None, ""):
        repo_root = Path(__file__).resolve().parents[3]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        return importlib.import_module("cli.setup.users.__main__")

    return importlib.import_module(__package__ + ".__main__")

_main = _import_main()

# Re-export public API
for _name in dir(_main):
    if _name.startswith("_"):
        continue
    globals()[_name] = getattr(_main, _name)

def main():
    return _main.main()

def __getattr__(name: str):
    return getattr(_main, name)

if __name__ == "__main__":
    raise SystemExit(main())
