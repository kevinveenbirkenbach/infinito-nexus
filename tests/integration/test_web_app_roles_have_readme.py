import unittest
from pathlib import Path
from typing import List, Optional


def find_repo_root(start: Path) -> Optional[Path]:
    """
    Walk up from `start` until we find a directory containing 'roles'.
    Returns the repo root (the directory that contains 'roles') or None.
    """
    for parent in [start] + list(start.parents):
        if (parent / "roles").is_dir():
            return parent
    return None


def web_app_role_dirs(root: Path) -> List[Path]:
    """Return all role directories that match roles/web-app-*."""
    roles_dir = root / "roles"
    return sorted([p for p in roles_dir.glob("web-app-*") if p.is_dir()])


class TestWebAppRolesHaveReadme(unittest.TestCase):
    """
    Ensures every role under roles/web-app-* contains a README.md.

    Why: The README is required for the role to be shown in the Web App Desktop.
    """

    @classmethod
    def setUpClass(cls):
        here = Path(__file__).resolve()
        repo_root = find_repo_root(here.parent)
        if repo_root is None:
            raise RuntimeError(
                f"Could not locate the repository root from {here}. "
                "Expected to find a 'roles/' directory in one of the parent folders."
            )
        cls.repo_root = repo_root
        cls.roles = web_app_role_dirs(repo_root)

    def test_roles_directory_present(self):
        self.assertTrue(
            (self.repo_root / "roles").is_dir(),
            f"'roles' directory not found at: {self.repo_root}",
        )

    def test_every_web_app_role_has_readme(self):
        missing = []
        for role_dir in self.roles:
            with self.subTest(role=role_dir.name):
                readme = role_dir / "README.md"
                if not readme.is_file():
                    missing.append(role_dir)

        if missing:
            formatted = "\n".join(f"- {p.relative_to(self.repo_root)}" for p in missing)
            self.fail(
                "The following roles are missing a README.md:\n"
                f"{formatted}\n\n"
                "A README.md is required so the role can be displayed in the Web App Desktop."
            )


if __name__ == "__main__":
    unittest.main()
