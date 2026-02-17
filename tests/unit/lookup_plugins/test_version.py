import os
import unittest
import tempfile
import importlib


class TestVersionLookup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Import the lookup plugin module once.
        # This assumes your repo structure allows importing "lookup_plugins.version".
        try:
            cls.plugin_module = importlib.import_module("lookup_plugins.version")
            cls.LookupModule = cls.plugin_module.LookupModule
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest(
                "Could not import lookup plugin 'lookup_plugins.version'. "
                "Make sure tests run with repo root on PYTHONPATH."
            ) from exc
        except Exception as exc:
            raise unittest.SkipTest(f"Failed importing lookup plugin: {exc}") from exc

        # Ensure ansible is importable (plugin depends on it)
        try:
            import ansible  # noqa: F401
        except Exception as exc:
            raise unittest.SkipTest(
                f"Ansible not available for unit tests: {exc}"
            ) from exc

    def _run_with_repo_layout(self, pyproject_content: str | None):
        """
        Creates a temporary repo-like layout:
          <tmp>/lookup_plugins/version.py   (simulated via patched __file__)
          <tmp>/pyproject.toml              (optional)
        Then executes the lookup plugin.
        """
        plugin_mod = self.plugin_module
        original_file = getattr(plugin_mod, "__file__", None)

        with tempfile.TemporaryDirectory() as tmp:
            lookup_dir = os.path.join(tmp, "lookup_plugins")
            os.makedirs(lookup_dir, exist_ok=True)

            # Place pyproject.toml at repo root (tmp) if requested
            if pyproject_content is not None:
                pyproject_path = os.path.join(tmp, "pyproject.toml")
                with open(pyproject_path, "w", encoding="utf-8") as f:
                    f.write(pyproject_content)

            # Patch module __file__ so the plugin resolves ../pyproject.toml from here
            plugin_mod.__file__ = os.path.join(lookup_dir, "version.py")

            try:
                plugin = self.LookupModule()
                # Plugin ignores terms/kwargs intentionally
                return plugin.run([])
            finally:
                # Restore __file__
                if original_file is None:
                    delattr(plugin_mod, "__file__")
                else:
                    plugin_mod.__file__ = original_file

    def test_reads_project_version(self):
        result = self._run_with_repo_layout(
            """
[project]
name = "demo"
version = "1.2.3"
"""
        )
        self.assertEqual(result, ["1.2.3"])

    def test_falls_back_to_poetry_version(self):
        result = self._run_with_repo_layout(
            """
[tool.poetry]
name = "demo"
version = "2.3.4"
"""
        )
        self.assertEqual(result, ["2.3.4"])

    def test_missing_pyproject_raises(self):
        from ansible.errors import AnsibleError

        with self.assertRaises(AnsibleError):
            self._run_with_repo_layout(pyproject_content=None)

    def test_missing_version_raises(self):
        from ansible.errors import AnsibleError

        with self.assertRaises(AnsibleError):
            self._run_with_repo_layout(
                """
[project]
name = "demo"
# no version here
"""
            )


if __name__ == "__main__":
    unittest.main()
