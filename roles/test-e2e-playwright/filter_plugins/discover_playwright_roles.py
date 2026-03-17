from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Set

from ansible.errors import AnsibleFilterError


def _to_role_set(raw: Optional[Iterable[str] | str], var_name: str) -> Set[str]:
    if raw is None:
        return set()

    if isinstance(raw, str):
        # Support CLI-style CSV extra-vars, e.g. allowed_applications=app1,app2
        return {item.strip() for item in raw.split(",") if item.strip()}

    try:
        return {str(item).strip() for item in raw if str(item).strip()}
    except TypeError as exc:
        raise AnsibleFilterError(f"{var_name} must be an iterable of role names or CSV string") from exc


def discover_playwright_roles(
    playbook_dir: str,
    only_roles: Optional[Iterable[str] | str] = None,
    skip_roles: Optional[Iterable[str] | str] = None,
) -> List[str]:
    base = Path(playbook_dir) / "roles"
    if not base.exists():
        raise AnsibleFilterError(f"roles dir not found: {base}")

    only = _to_role_set(only_roles, "only_roles")
    skip = _to_role_set(skip_roles, "skip_roles")

    found: List[str] = []
    for env_file in base.rglob("tests/playwright/env.j2"):
        # env.j2 is the stable marker
        role_name = env_file.parents[2].name  # .../roles/<role>/tests/playwright/env.j2
        found.append(role_name)

    # stable, unique
    uniq = sorted(set(found))

    if only:
        uniq = [role for role in uniq if role in only]
    if skip:
        uniq = [role for role in uniq if role not in skip]

    return uniq


class FilterModule(object):
    def filters(self):
        return {
            "discover_playwright_roles": discover_playwright_roles,
        }
