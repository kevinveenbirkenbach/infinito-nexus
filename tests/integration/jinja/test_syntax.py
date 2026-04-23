# tests/integration/test_jinja2_syntax.py

import os
import unittest
from jinja2 import Environment, exceptions, select_autoescape


class TestJinja2Syntax(unittest.TestCase):
    def test_all_j2_templates_have_valid_syntax(self):
        """
        Recursively find all .j2 files from the project root and try to parse them.
        A SyntaxError in any template fails the test.
        """
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        env = Environment(autoescape=select_autoescape())

        failures = []

        for root, _dirs, files in os.walk(project_root):
            for fname in files:
                if fname.endswith(".j2"):
                    path = os.path.join(root, fname)
                    with open(path, "r", encoding="utf-8") as f:
                        src = f.read()
                    try:
                        env.parse(src)
                    except exceptions.TemplateSyntaxError as e:
                        failures.append(f"{path}:{e.lineno} – {e.message}")

        if failures:
            self.fail(
                "Syntax errors found in Jinja2 templates:\n" + "\n".join(failures)
            )


if __name__ == "__main__":
    unittest.main()
