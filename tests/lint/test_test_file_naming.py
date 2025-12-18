from pathlib import Path
import unittest


class TestTestFileNaming(unittest.TestCase):
    """
    Test-linter that enforces all Python files in the tests/
    directory to start with the 'test_' prefix.

    This guarantees consistent test naming and reliable
    test discovery.
    """

    def test_all_python_files_use_test_prefix(self):
        tests_root = Path(__file__).resolve().parents[1]

        invalid_files = []

        for path in tests_root.rglob("*.py"):
            # Explicitly allow package initializers
            if path.name == "__init__.py":
                continue

            if not path.name.startswith("test_"):
                invalid_files.append(path.relative_to(tests_root))

        if invalid_files:
            self.fail(
                "The following Python files do not start with 'test_':\n"
                + "\n".join(f"- {p}" for p in invalid_files)
            )


if __name__ == "__main__":
    unittest.main()
