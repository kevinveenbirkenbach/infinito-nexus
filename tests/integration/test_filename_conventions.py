import os
import unittest

class TestFilenameConventions(unittest.TestCase):
    """
    Integration test to ensure README.md and TODO.md files
    are always written in uppercase (README.md / TODO.md).
    """

    def test_readme_and_todo_filenames_are_uppercase(self):
        bad_files = []
        for root, _, files in os.walk("."):
            for filename in files:
                lower = filename.lower()
                if lower in ("readme.md", "todo.md"):
                    if filename not in ("README.md", "TODO.md"):
                        bad_files.append(os.path.join(root, filename))

        msg = (
            "The following files violate uppercase naming convention "
            "(must be README.md or TODO.md):\n- " + "\n- ".join(bad_files)
        ) if bad_files else None

        self.assertEqual(bad_files, [], msg)

if __name__ == "__main__":
    unittest.main()
