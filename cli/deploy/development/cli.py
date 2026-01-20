from __future__ import annotations

import importlib.util
import runpy
import sys
from typing import Optional


def _module_exists(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _dispatch(argv: list[str]) -> int:
    """
    Dynamic dispatcher for nested CLI command packages.

    A command package is identified by existence of:
        cli/<segments>/__main__.py

    The integration test calls:
        python cli/__main__.py <segments...> --help --no-signal

    This dispatcher resolves the *longest* prefix of segments that forms a module:
        cli.<segments>.__main__
    and executes it as __main__ via runpy.

    Example:
      argv = ["deploy", "development", "--help", "--no-signal"]
      -> module "cli.deploy.development.__main__"
    """
    if not argv:
        # Show a minimal help; keep it simple.
        print("Usage: python -m cli <command> [<subcommand> ...] [args]")
        print("Hint: run `python -m cli --help` or `python -m cli <command> --help`.")
        return 0

    # Find the longest prefix that matches a command package module
    best_len = 0
    best_module: Optional[str] = None

    for i in range(1, len(argv) + 1):
        mod = "cli." + ".".join(argv[:i]) + ".__main__"
        if _module_exists(mod):
            best_len = i
            best_module = mod

    if not best_module:
        # Keep error format compatible with your current expectation.
        # (Your failing output was: "Error: command 'deploy development --help' not found.")
        joined = " ".join(argv)
        print(f"Error: command '{joined}' not found.")
        return 1

    # Rewrite argv so the subcommand module sees only its own args
    sub_argv = argv[best_len:]
    sys.argv = [best_module] + sub_argv

    # Execute the module like `python -m ...`
    runpy.run_module(best_module, run_name="__main__")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    # We intentionally do NOT parse args here; we delegate to subcommands.
    argv = list(sys.argv[1:] if argv is None else argv)

    # Optional global flags could be handled here if you want.
    # For now, we just pass everything through.
    return int(_dispatch(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
