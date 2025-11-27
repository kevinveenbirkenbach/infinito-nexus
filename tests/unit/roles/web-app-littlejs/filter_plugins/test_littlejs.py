import unittest
import importlib.util
from pathlib import Path


def _load_littlejs_module():
    """
    Load the littlejs filter plugin directly from the roles path.
    Works even with hyphens in directory names.
    """
    here = Path(__file__).resolve()
    plugin_path = (
        here.parents[5]
        / "roles"
        / "web-app-littlejs"
        / "filter_plugins"
        / "littlejs.py"
    )

    spec = importlib.util.spec_from_file_location("littlejs_filter", plugin_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestLittlejsHref(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        module = _load_littlejs_module()
        # Store original function; we will always access it via type(self)
        cls._littlejs_href = module.littlejs_href

    def test_returns_hash_if_no_file(self):
        href = type(self)._littlejs_href({}, "https", "littlejs.example.com")
        self.assertEqual(href, "#")

    def test_full_example_project(self):
        example = {"file": "starter", "is_project": True}
        href = type(self)._littlejs_href(example, "https", "littlejs.example.com")
        self.assertEqual(
            href,
            "https://littlejs.example.com/examples/starter/"
        )

    def test_short_example_uses_runner(self):
        # no is_project → False by default
        example = {"file": "clock.js"}
        href = type(self)._littlejs_href(example, "https", "littlejs.example.com")
        self.assertEqual(
            href,
            "https://littlejs.example.com/examples/shorts/run.html?file=clock.js"
        )

    def test_respects_protocol_and_domain(self):
        example = {"file": "platformer", "is_project": True}
        href = type(self)._littlejs_href(example, "http", "littlejs.infinito.nexus")
        self.assertEqual(
            href,
            "http://littlejs.infinito.nexus/examples/platformer/"
        )


if __name__ == "__main__":
    unittest.main()
