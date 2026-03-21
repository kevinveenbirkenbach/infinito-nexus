import os
import unittest
from pathlib import Path


def _gha_escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _emit_missing_playwright_spec_warning(repo_root: Path, role_path: Path) -> None:
    spec_file = role_path / "files" / "playwright.spec.js"
    relative_spec_path = spec_file.relative_to(repo_root).as_posix()
    message = f"{role_path.name} has no files/playwright.spec.js (non-blocking)"

    if os.environ.get("GITHUB_ACTIONS") != "true":
        return

    print(
        "::warning "
        f"file={_gha_escape(relative_spec_path)},"
        "title=Missing Playwright Spec::"
        f"{_gha_escape(message)}"
    )


class TestWebAppRolesHavePlaywrightSpec(unittest.TestCase):
    def test_web_app_roles_playwright_spec_warn_only(self):
        """
        Check all roles/web-app-* for files/playwright.spec.js.
        Missing specs are reported as warnings but do not fail the test.
        """
        repo_root = Path(__file__).resolve().parent.parent.parent
        roles_dir = repo_root / "roles"
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
                _emit_missing_playwright_spec_warning(repo_root, role_path)

        if missing:
            if os.environ.get("GITHUB_ACTIONS") == "true":
                print("Missing Playwright specs (non-blocking): " + ", ".join(missing))
            else:
                warning_lines = "\n".join(f"- {role}" for role in missing)
                print(
                    "\n[WARNING] The following web-app roles have no files/playwright.spec.js "
                    "(non-blocking):\n" + warning_lines
                )

        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
