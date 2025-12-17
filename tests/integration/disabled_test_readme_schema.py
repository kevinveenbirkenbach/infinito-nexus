import unittest
import re
import yaml
from pathlib import Path

# Define the required schema headings
REQUIRED_HEADINGS = [
    "Description",
    "Overview",
    "Features",
    "Further Resources",
]


class TestReadmeSchema(unittest.TestCase):
    def test_readme_has_required_sections_and_title(self):
        """
        Integration test that verifies each role's README.md contains all required sections
        and, if vars/main.yml exists, that the title contains the application_id (case-insensitive).
        """
        # Determine the roles directory (two levels up from current file)
        roles_dir = Path(__file__).parents[2] / "roles"
        self.assertTrue(roles_dir.exists(), f"Roles directory not found at {roles_dir}")

        for role_dir in roles_dir.iterdir():
            if not role_dir.is_dir():
                continue

            with self.subTest(role=role_dir.name):
                # Check README.md exists
                readme_path = role_dir / "README.md"
                self.assertTrue(
                    readme_path.exists(),
                    f"Role '{role_dir.name}' is missing a README.md",
                )

                content = readme_path.read_text(encoding="utf-8")
                # Verify required headings are present (multiline)
                for heading in REQUIRED_HEADINGS:
                    pattern = rf"(?m)^##\s+{re.escape(heading)}"
                    self.assertRegex(
                        content,
                        pattern,
                        f"README.md for role '{role_dir.name}' is missing required section: '{heading}'",
                    )

                # If vars/main.yml exists, check application_id and title
                vars_path = role_dir / "vars" / "main.yml"
                if vars_path.exists():
                    vars_content = vars_path.read_text(encoding="utf-8")
                    try:
                        data = yaml.safe_load(vars_content)
                    except Exception as e:
                        self.fail(
                            f"Failed to parse YAML for role '{role_dir.name}': {e}"
                        )

                    app_id = data.get("application_id")
                    self.assertIsNotNone(
                        app_id,
                        f"application_id not found in {vars_path} for role '{role_dir.name}'",
                    )

                    # Verify README title contains application_id (case-insensitive, multiline)
                    title_regex = re.compile(rf"(?mi)^#.*{re.escape(str(app_id))}.*")
                    self.assertRegex(
                        content,
                        title_regex,
                        f"README.md title does not contain application_id '{app_id}' for role '{role_dir.name}'",
                    )


if __name__ == "__main__":
    unittest.main()
