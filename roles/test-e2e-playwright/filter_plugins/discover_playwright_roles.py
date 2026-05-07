from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ansible.errors import AnsibleFilterError


def _to_role_set(raw: Iterable[str] | str | None, var_name: str) -> set[str]:
    if raw is None:
        return set()

    if isinstance(raw, str):
        # Support CLI-style CSV extra-vars, e.g. allowed_applications=app1,app2
        return {item.strip() for item in raw.split(",") if item.strip()}

    try:
        return {str(item).strip() for item in raw if str(item).strip()}
    except TypeError as exc:
        raise AnsibleFilterError(
            f"{var_name} must be an iterable of role names or CSV string"
        ) from exc


def discover_playwright_roles(
    playbook_dir: str,
    only_roles: Iterable[str] | str | None = None,
    skip_roles: Iterable[str] | str | None = None,
) -> list[str]:
    base = Path(playbook_dir) / "roles"
    if not base.exists():
        raise AnsibleFilterError(f"roles dir not found: {base}")

    only = _to_role_set(only_roles, "only_roles")
    skip = _to_role_set(skip_roles, "skip_roles")

    found: list[str] = []

    # Current marker for Playwright-enabled app roles:
    # .../roles/<role>/templates/playwright.env.j2
    for env_file in base.rglob("templates/playwright.env.j2"):
        # nocheck: project-root-import  walking from a discovered glob match (<role>/templates/...) up to its role dir, not the repo root
        role_name = env_file.parents[1].name
        found.append(role_name)

    # stable, unique
    uniq = sorted(set(found))

    if only:
        uniq = [role for role in uniq if role in only]
    if skip:
        uniq = [role for role in uniq if role not in skip]

    return uniq


class FilterModule:
    def filters(self):
        return {
            "discover_playwright_roles": discover_playwright_roles,
        }
