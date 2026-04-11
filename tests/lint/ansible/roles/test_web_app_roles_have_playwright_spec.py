import unittest
from pathlib import Path

from utils.annotations.message import warning


def repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise AssertionError("Repository root not found from test path.")


def _emit_missing_playwright_spec_warning(repo_root: Path, role_path: Path) -> None:
    spec_file = role_path / "files" / "playwright.spec.js"
    relative_spec_path = spec_file.relative_to(repo_root).as_posix()
    message = f"{role_path.name} has no files/playwright.spec.js (non-blocking)"
    warning(message, title="Missing Playwright Spec", file=relative_spec_path)


class TestWebAppRolesHavePlaywrightSpec(unittest.TestCase):
    def test_web_app_roles_playwright_spec_warn_only(self):
        """
        Check all roles/web-app-* for files/playwright.spec.js.
        Missing specs are reported as warnings but do not fail the test.
        """
        root = repo_root()
        roles_dir = root / "roles"
        self.assertTrue(
            roles_dir.is_dir(), f"'roles' directory not found at: {roles_dir}"
        )

        missing = []
        for role_path in sorted(roles_dir.iterdir()):
            if not (role_path.is_dir() and role_path.name.startswith("web-app-")):
                continue

            spec_file = role_path / "files" / "playwright.spec.js"
            if not spec_file.is_file():
                missing.append(role_path.name)
                _emit_missing_playwright_spec_warning(root, role_path)

        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
