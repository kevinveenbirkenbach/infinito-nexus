import os
import glob
import yaml
import unittest


def find_application_ids():
    """
    Scans all roles/*/vars/main.yml files and collects application_id values.
    Returns a dict mapping application_id to list of file paths where it appears.
    """
    ids = {}
    # Wenn der Test unter tests/integration liegt, gehen wir zwei Ebenen hoch zum Projekt-Root
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    pattern = os.path.join(base_dir, "roles", "*", "vars", "main.yml")

    for file_path in glob.glob(pattern):
        with open(file_path, "r") as f:
            data = yaml.safe_load(f) or {}
        app_id = data.get("application_id")
        if app_id is not None:
            ids.setdefault(app_id, []).append(file_path)
    return ids


class TestUniqueApplicationId(unittest.TestCase):
    def test_application_ids_are_unique(self):
        ids = find_application_ids()
        duplicates = {app_id: paths for app_id, paths in ids.items() if len(paths) > 1}
        if duplicates:
            messages = []
            for app_id, paths in duplicates.items():
                file_list = "\n    ".join(paths)
                messages.append(
                    f"application_id '{app_id}' found in multiple files:\n    {file_list}"
                )
            self.fail("\n\n".join(messages))


if __name__ == "__main__":
    unittest.main(verbosity=2)
