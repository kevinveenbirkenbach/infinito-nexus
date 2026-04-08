"""Warn about templated Dockerfiles that should become plain files.

Roles that still ship ``templates/Dockerfile.j2`` are reported as warnings so
that maintainers can migrate them to ``files/Dockerfile`` over time without
blocking CI. Plain Dockerfiles are preferred because they are easier to test
and maintain and provide a cleaner separation of concerns. Variables can often
be moved into ``templates/env.j2`` instead of being rendered into the
Dockerfile itself.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from utils.gha.annotations import warning

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ROLES_ROOT = _REPO_ROOT / "roles"


def _collect_templated_dockerfiles() -> list[Path]:
    templated: list[Path] = []
    for dockerfile_j2 in sorted(_ROLES_ROOT.glob("*/templates/Dockerfile.j2")):
        plain_dockerfile = dockerfile_j2.parents[1] / "files" / "Dockerfile"
        if plain_dockerfile.is_file():
            continue
        templated.append(dockerfile_j2)
    return templated


def _warning_message(relative_path: str) -> str:
    return f"{relative_path} uses Dockerfile.j2 instead of files/Dockerfile. {_warning_reason()}"


def _warning_reason() -> str:
    return (
        "Prefer a plain Dockerfile because Dockerfiles are easier to test and "
        "maintain and provide better separation of concerns. Variables can "
        "usually be moved to templates/env.j2 instead."
    )


def _emit_warning(dockerfile_j2: Path) -> None:
    relative_path = dockerfile_j2.relative_to(_REPO_ROOT).as_posix()
    message = _warning_message(relative_path)
    warning(message, title="Templated Dockerfile", file=relative_path)


class TestDockerfileTemplates(unittest.TestCase):
    """Warn when roles still use templates/Dockerfile.j2."""

    def test_dockerfile_j2_warns_only(self) -> None:
        self.assertTrue(
            _ROLES_ROOT.is_dir(), f"'roles' directory not found at: {_ROLES_ROOT}"
        )

        templated = _collect_templated_dockerfiles()

        if templated:
            for dockerfile_j2 in templated:
                _emit_warning(dockerfile_j2)

        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
