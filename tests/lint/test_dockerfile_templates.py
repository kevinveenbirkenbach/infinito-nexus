"""Warn about templated Dockerfiles that should become plain files.

Roles that still ship ``templates/Dockerfile.j2`` are reported as warnings so
that maintainers can migrate them to ``files/Dockerfile`` over time without
blocking CI. Plain Dockerfiles are preferred because they are easier to test
and maintain and provide a cleaner separation of concerns. Variables can often
be moved into ``templates/env.j2`` instead of being rendered into the
Dockerfile itself.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ROLES_ROOT = _REPO_ROOT / "roles"


def _gha_escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


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

    if os.environ.get("GITHUB_ACTIONS") != "true":
        return

    print(
        "::warning "
        f"file={_gha_escape(relative_path)},"
        "title=Templated Dockerfile::"
        f"{_gha_escape(message)}"
    )


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

            if os.environ.get("GITHUB_ACTIONS") == "true":
                print(
                    "Templated Dockerfiles detected (non-blocking): "
                    + ", ".join(
                        dockerfile_j2.relative_to(_REPO_ROOT).as_posix()
                        for dockerfile_j2 in templated
                    )
                )
            else:
                warning_lines = "\n".join(
                    f"- {dockerfile_j2.relative_to(_REPO_ROOT).as_posix()}"
                    for dockerfile_j2 in templated
                )
                print(
                    "\n[WARNING] The following templated Dockerfiles should be "
                    "migrated to files/Dockerfile (non-blocking).\n"
                    + _warning_reason()
                    + "\nAffected paths:\n"
                    + warning_lines
                )

        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
