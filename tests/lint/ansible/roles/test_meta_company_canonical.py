"""Lint: every roles/*/meta/main.yml MUST declare the canonical
``galaxy_info.company`` block-scalar value.

Galaxy metadata accumulated drift over time — single-line, single-quoted
multi-line, double-quoted with ``\\n``, block-scalar, Unicode non-breaking
hyphens, and a recurring ``Birchenbach`` typo. Normalizing on one exact
string keeps the field auto-grep-able and avoids re-introducing the
broken multi-line forms.

The canonical YAML form is::

    galaxy_info:
      ...
      license: Infinito.Nexus Community License (Non-Commercial)
      company: |
        Kevin Veen-Birkenbach
        Consulting & Coaching Solutions
        https://www.veen.world

Parsed, that yields the multi-line string compared below.
"""

import unittest

from utils.cache.yaml import load_yaml
from utils.roles.mapping import ROLE_FILE_META_MAIN

from . import PROJECT_ROOT

CANONICAL_COMPANY = (
    "Kevin Veen-Birkenbach\nConsulting & Coaching Solutions\nhttps://www.veen.world\n"
)


class TestMetaCompanyCanonical(unittest.TestCase):
    def test_every_role_meta_has_canonical_company(self) -> None:
        roles_dir = PROJECT_ROOT / "roles"
        self.assertTrue(
            roles_dir.is_dir(), f"'roles' directory not found at: {roles_dir}"
        )

        violations: list[str] = []
        for role_path in sorted(roles_dir.iterdir()):
            if not role_path.is_dir():
                continue

            meta_main = role_path / ROLE_FILE_META_MAIN
            if not meta_main.is_file():
                continue

            data = load_yaml(meta_main, default_if_missing={}) or {}
            galaxy_info = (data or {}).get("galaxy_info")
            if not isinstance(galaxy_info, dict):
                continue

            rel = meta_main.relative_to(PROJECT_ROOT).as_posix()
            company = galaxy_info.get("company")
            if company is None:
                violations.append(f"{rel}: galaxy_info.company is missing")
                continue
            if company != CANONICAL_COMPANY:
                violations.append(
                    f"{rel}: galaxy_info.company differs from canonical "
                    f"value (got {company!r})"
                )

        self.assertEqual(
            violations,
            [],
            "\n\n".join(
                [
                    "Every roles/*/meta/main.yml with galaxy_info MUST set "
                    "company to the canonical block-scalar value:\n"
                    "  company: |\n"
                    "    Kevin Veen-Birkenbach\n"
                    "    Consulting & Coaching Solutions\n"
                    "    https://www.veen.world\n"
                    "Offenders:",
                    *violations,
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
