from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from ansible.errors import AnsibleFilterError


def _is_cypress_role_dir(path: Path) -> bool:
    # roles/<role>/tests/cypress
    parts = path.parts
    try:
        i = parts.index("roles")
    except ValueError:
        return False

    # need at least: roles/<role>/tests/cypress
    if len(parts) < i + 4:
        return False

    return parts[i + 2] == "tests" and parts[i + 3] == "cypress"


def discover_cypress_roles(
    playbook_dir: str,
    only_roles: Optional[Iterable[str]] = None,
    skip_roles: Optional[Iterable[str]] = None,
) -> List[str]:
    base = Path(playbook_dir) / "roles"
    if not base.exists():
        raise AnsibleFilterError(f"roles dir not found: {base}")

    only = set(only_roles or [])
    skip = set(skip_roles or [])

    found: List[str] = []
    for env_file in base.rglob("tests/cypress/env.j2"):
        # env.j2 is the stable marker
        role_name = env_file.parents[2].name  # .../roles/<role>/tests/cypress/env.j2
        found.append(role_name)

    # stable, unique
    uniq = sorted(set(found))

    if only:
        uniq = [r for r in uniq if r in only]
    if skip:
        uniq = [r for r in uniq if r not in skip]

    return uniq


class FilterModule(object):
    def filters(self):
        return {
            "discover_cypress_roles": discover_cypress_roles,
        }
