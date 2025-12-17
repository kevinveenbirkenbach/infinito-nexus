import os
import unittest
import yaml


class TestYamlSyntax(unittest.TestCase):
    def test_all_yml_files_are_valid_yaml(self):
        """
        Walk the entire repository, find all *.yml files and try to parse them
        with yaml.safe_load(). Fail the test if any file contains invalid YAML.
        """
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        invalid = []

        for dirpath, dirnames, filenames in os.walk(repo_root):
            # skip hidden directories (like .git, .venv, etc.)
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fname in filenames:
                if not fname.endswith(".yml"):
                    continue
                full = os.path.join(dirpath, fname)
                # skip any large auto‐generated files if needed:
                # if 'some/path/to/skip' in full: continue

                try:
                    with open(full, "r") as f:
                        yaml.safe_load(f)
                except yaml.YAMLError as e:
                    invalid.append((full, str(e)))
                except Exception as e:
                    invalid.append((full, f"Unexpected error: {e}"))

        if invalid:
            msg_lines = [
                f"{path}: {err.splitlines()[0]}"  # just the first line of the error
                for path, err in invalid
            ]
            self.fail(
                "Found invalid YAML in the following files:\n" + "\n".join(msg_lines)
            )


if __name__ == "__main__":
    unittest.main()
