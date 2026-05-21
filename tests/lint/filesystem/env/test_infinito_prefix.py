"""Every key declared in `env/*.env` must carry the `INFINITO_` prefix.

The shared namespace exists so project env-vars never collide with
generic shell or Ansible-role variables of the same short name. Any
key without the prefix is either leaking into the wrong scope or
needs the prefix added.
"""

from __future__ import annotations

import re
import unittest
from dataclasses import dataclass
from typing import TYPE_CHECKING

from utils.cache.files import read_text

from . import PROJECT_ROOT

if TYPE_CHECKING:
    from pathlib import Path

_KEY_RE = re.compile(r"^\s*(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=")
_INFINITO_KEY_RE = re.compile(r"^INFINITO_[A-Z0-9_]+$")


@dataclass(frozen=True)
class _Violation:
    file: str
    line_no: int
    key: str


def _scan_file(path: Path) -> list[_Violation]:
    rel = path.relative_to(PROJECT_ROOT).as_posix()
    out: list[_Violation] = []
    for index, line in enumerate(read_text(str(path)).splitlines(), start=1):
        match = _KEY_RE.match(line)
        if match is None:
            continue
        key = match.group("key")
        if _INFINITO_KEY_RE.match(key):
            continue
        out.append(_Violation(rel, index, key))
    return out


def _scan_targets() -> list[Path]:
    return sorted((PROJECT_ROOT / "env").glob("*.env"))


class TestEnvFilesInfinitoPrefix(unittest.TestCase):
    def test_every_env_file_key_carries_infinito_prefix(self) -> None:
        targets = _scan_targets()
        self.assertTrue(targets, "no env/*.env files found to scan")

        violations: list[_Violation] = []
        for path in targets:
            violations.extend(_scan_file(path))

        if not violations:
            return

        lines = [
            f"env/*.env keys without the INFINITO_ prefix "
            f"({len(violations)} violations):",
            "",
            "Every key in env/*.env must start with INFINITO_ so it cannot "
            "collide with generic shell or Ansible-role variables of the "
            "same short name. Rename the key to INFINITO_<NAME> (and update "
            "callers) or move it out of env/*.env if it is not part of the "
            "project's INFINITO_* namespace.",
            "",
            "Offenders:",
        ]
        lines.extend(f"  {v.file}:{v.line_no}: {v.key}" for v in violations)
        self.fail("\n".join(lines))


if __name__ == "__main__":
    unittest.main()
