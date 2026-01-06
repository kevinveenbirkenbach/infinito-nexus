from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable, Optional, Set, Tuple

import yaml


def _repo_root() -> Path:
    """
    Determine repository root by locating the 'cli/' directory.
    This makes the tool independent from the current working directory.
    """
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "cli").is_dir():
            return parent
    raise RuntimeError("Failed to locate repository root (missing 'cli/' directory).")


def _extract_lifecycle(meta: dict[str, Any]) -> str:
    """
    Supports both:
      galaxy_info:
        lifecycle: stable

    and an optional future form:
      galaxy_info:
        lifecycle:
          stage: stable
    """
    gi = meta.get("galaxy_info") or {}
    lifecycle = gi.get("lifecycle")

    if isinstance(lifecycle, str):
        return lifecycle.strip().lower()

    if isinstance(lifecycle, dict):
        stage = lifecycle.get("stage")
        if isinstance(stage, str):
            return stage.strip().lower()

    return ""


def _iter_role_meta_files(roles_dir: Path) -> Iterable[Tuple[str, Path]]:
    """
    Yields (role_name, meta_file_path) for roles that have a meta/main.yml.
    """
    if not roles_dir.exists() or not roles_dir.is_dir():
        return

    for role_dir in sorted(p for p in roles_dir.iterdir() if p.is_dir()):
        meta_file = role_dir / "meta" / "main.yml"
        if meta_file.is_file():
            yield role_dir.name, meta_file


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to read/parse YAML: {path}: {exc}") from exc

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise RuntimeError(
            f"Expected a YAML mapping in {path}, got {type(data).__name__}"
        )
    return data


def filter_roles(
    roles_dir: Path,
    mode: str,
    statuses: Set[str],
    selection: Optional[Set[str]] = None,
    include_missing_lifecycle_on_blacklist: bool = True,
) -> list[str]:
    matched: list[str] = []

    for role_name, meta_file in _iter_role_meta_files(roles_dir):
        if selection is not None and role_name not in selection:
            continue

        meta = _load_yaml(meta_file)
        lifecycle = _extract_lifecycle(meta)

        if mode == "whitelist":
            if lifecycle in statuses:
                matched.append(role_name)
        else:  # blacklist
            if lifecycle == "":
                if include_missing_lifecycle_on_blacklist:
                    matched.append(role_name)
                continue

            if lifecycle not in statuses:
                matched.append(role_name)

    return sorted(matched)


def build_parser() -> argparse.ArgumentParser:
    default_roles_dir = _repo_root() / "roles"

    p = argparse.ArgumentParser(
        prog="infinito meta roles lifecycle_filter",
        description="Print role names (space-separated) filtered by galaxy_info.lifecycle "
        "in roles/*/meta/main.yml.\n\n"
        "Examples:\n"
        "  infinito meta roles lifecycle_filter whitelist stable rc\n"
        "  infinito meta roles lifecycle_filter blacklist deprecated eol\n"
        "  infinito meta roles lifecycle_filter whitelist stable "
        "--selection web-app-matomo docker-keycloak\n",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    p.add_argument(
        "mode",
        choices=["whitelist", "blacklist"],
        help="Filtering mode.",
    )
    p.add_argument(
        "statuses",
        nargs="+",
        help="Lifecycle statuses (space-separated), e.g. stable beta rc deprecated eol",
    )
    p.add_argument(
        "--roles-dir",
        type=Path,
        default=default_roles_dir,
        help=f"Roles directory to scan (default: {default_roles_dir})",
    )
    p.add_argument(
        "--selection",
        nargs="+",
        help="Optional whitelist of role names. "
        "Only roles contained in this list are returned if filters match.",
    )
    p.add_argument(
        "--exclude-missing",
        action="store_true",
        help="In blacklist mode: exclude roles with missing lifecycle instead of including them.",
    )

    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    roles_dir: Path = args.roles_dir
    statuses = {s.strip().lower() for s in args.statuses if s.strip()}
    selection = (
        {s.strip() for s in args.selection if s.strip()} if args.selection else None
    )

    if not roles_dir.is_dir():
        print(f"Error: roles directory not found: {roles_dir}", file=sys.stderr)
        return 1

    try:
        role_names = filter_roles(
            roles_dir=roles_dir,
            mode=args.mode,
            statuses=statuses,
            selection=selection,
            include_missing_lifecycle_on_blacklist=not args.exclude_missing,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    # Output: role names separated by whitespaces
    sys.stdout.write(" ".join(role_names) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
