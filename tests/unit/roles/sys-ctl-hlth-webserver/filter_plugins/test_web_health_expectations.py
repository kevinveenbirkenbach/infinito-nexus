# tests/unit/roles/sys-ctl-hlth-webserver/filter_plugins/test_web_health_expectations.py
import os
import unittest
import importlib.util
from unittest.mock import patch


def load_module_from_path(mod_name: str, path: str):
    """Dynamically load a module from a filesystem path."""
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


class TestWebHealthExpectationsFilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Compute repo root from this test file location
        here = os.path.abspath(os.path.dirname(__file__))
        # tests/unit/roles/sys-ctl-hlth-webserver/filter_plugins/ -> repo root is 5 levels up
        cls.ROOT = os.path.abspath(os.path.join(here, "..", "..", "..", "..", ".."))

        cls.module_path = os.path.join(
            cls.ROOT, "roles", "sys-ctl-hlth-webserver", "filter_plugins", "web_health_expectations.py"
        )
        if not os.path.isfile(cls.module_path):
            raise FileNotFoundError(f"Cannot find web_health_expectations.py at {cls.module_path}")

        # Load the filter module once for all tests
        cls.mod = load_module_from_path("web_health_expectations", cls.module_path)

    def setUp(self):
        # Fresh mock for get_app_conf per test
        self.get_app_conf_patch = patch.object(self.mod, "get_app_conf")
        self.mock_get_app_conf = self.get_app_conf_patch.start()

    def tearDown(self):
        self.get_app_conf_patch.stop()

    def _configure_returns(self, mapping):
        """
        Provide a dict keyed by (app_id, key) -> value.
        get_app_conf(...) will return mapping.get((app_id, key), default)
        """
        def side_effect(applications, app_id, key, strict=False, default=None):
            return mapping.get((app_id, key), default)
        self.mock_get_app_conf.side_effect = side_effect

    # ------------ Required selection --------------

    def test_raises_when_group_names_missing(self):
        apps = {"app-a": {}}
        with self.assertRaises(ValueError):
            self.mod.web_health_expectations(apps, group_names=None)

    def test_raises_when_group_names_empty_variants(self):
        apps = {"app-a": {}}
        with self.assertRaises(ValueError):
            self.mod.web_health_expectations(apps, group_names=[])
        with self.assertRaises(ValueError):
            self.mod.web_health_expectations(apps, group_names="")
        with self.assertRaises(ValueError):
            self.mod.web_health_expectations(apps, group_names=" ,  ")

    # ---- Non-mapping apps short-circuit (but group_names still required) ----

    def test_non_mapping_returns_empty_dict(self):
        expectations = self.mod.web_health_expectations(applications=["not", "a", "mapping"], group_names=["any"])
        self.assertEqual(expectations, {})

    # ------------ Flat canonical -----------------

    def test_flat_canonical_with_default_status(self):
        apps = {"app-a": {}}
        self._configure_returns({
            ("app-a", "server.domains.canonical"): ["a.example.org"],
            ("app-a", "server.domains.aliases"):   [],
            ("app-a", "server.status_codes"):      {"default": 405},
        })
        out = self.mod.web_health_expectations(apps, group_names=["app-a"])
        self.assertEqual(out["a.example.org"], [405])

    def test_flat_canonical_invalid_default_falls_back_to_DEFAULT_OK(self):
        apps = {"app-x": {}}
        self._configure_returns({
            ("app-x", "server.domains.canonical"): ["x.example.org"],
            ("app-x", "server.domains.aliases"):   [],
            ("app-x", "server.status_codes"):      {"default": 700},  # invalid HTTP code
        })
        out = self.mod.web_health_expectations(apps, group_names=["app-x"])
        self.assertEqual(out["x.example.org"], [200, 302, 301])

    # ------------ Keyed canonical ----------------

    def test_keyed_canonical_with_per_key_overrides_and_default(self):
        apps = {"app-d": {}}
        self._configure_returns({
            ("app-d", "server.domains.canonical"): {
                "api":  "api.d.example.org",
                "web":  "web.d.example.org",
                "view": ["v1.d.example.org", "v2.d.example.org"],
            },
            ("app-d", "server.domains.aliases"):   ["alias.d.example.org"],
            ("app-d", "server.status_codes"):      {"api": 404, "default": 405},
        })
        out = self.mod.web_health_expectations(apps, group_names=["app-d"])

        self.assertEqual(out["api.d.example.org"], [404])   # per-key override wins
        self.assertEqual(out["web.d.example.org"], [405])   # default used
        self.assertEqual(out["v1.d.example.org"], [405])    # default used
        self.assertEqual(out["v2.d.example.org"], [405])    # default used
        self.assertEqual(out["alias.d.example.org"], [301]) # aliases always redirect

    def test_keyed_canonical_invalid_key_and_default_falls_back(self):
        apps = {"app-y": {}}
        self._configure_returns({
            ("app-y", "server.domains.canonical"): {"web": ["y.example.org"]},
            ("app-y", "server.domains.aliases"):   [],
            ("app-y", "server.status_codes"):      {"web": 999},  # invalid; default missing
        })
        out = self.mod.web_health_expectations(apps, group_names=["app-y"])
        self.assertEqual(out["y.example.org"], [200, 302, 301])

    # ------------ Selection by group_names -------

    def test_selection_by_group_names_list(self):
        apps = {"app-a": {}, "app-b": {}, "app-c": {}}
        self._configure_returns({
            ("app-a", "server.domains.canonical"): ["a.example.org"],
            ("app-a", "server.domains.aliases"):   [],
            ("app-a", "server.status_codes"):      {"default": 200},

            ("app-b", "server.domains.canonical"): ["b.example.org"],
            ("app-b", "server.domains.aliases"):   [],
            ("app-b", "server.status_codes"):      {"default": 405},

            ("app-c", "server.domains.canonical"): ["c.example.org"],
            ("app-c", "server.domains.aliases"):   ["alias.c.example.org"],
            ("app-c", "server.status_codes"):      {},
        })

        out = self.mod.web_health_expectations(apps, group_names=["app-a", "app-c"])
        self.assertIn("a.example.org", out)
        self.assertIn("c.example.org", out)
        self.assertIn("alias.c.example.org", out)
        self.assertNotIn("b.example.org", out)

    def test_selection_by_group_names_string(self):
        apps = {"app-a": {}, "app-b": {}}
        self._configure_returns({
            ("app-a", "server.domains.canonical"): ["a.example.org"],
            ("app-a", "server.domains.aliases"):   [],
            ("app-a", "server.status_codes"):      {"default": 200},

            ("app-b", "server.domains.canonical"): ["b.example.org"],
            ("app-b", "server.domains.aliases"):   [],
            ("app-b", "server.status_codes"):      {"default": 405},
        })
        out = self.mod.web_health_expectations(apps, group_names="app-a, app-c ")
        self.assertIn("a.example.org", out)
        self.assertNotIn("b.example.org", out)

    # ------------ Aliases & filtering ------------

    def test_aliases_are_always_301(self):
        apps = {"app-f": {}}
        self._configure_returns({
            ("app-f", "server.domains.canonical"): ["f.example.org"],
            ("app-f", "server.domains.aliases"):   ["alias1.example.org", "alias2.example.org"],
            ("app-f", "server.status_codes"):      {"default": 200},
        })
        out = self.mod.web_health_expectations(apps, group_names=["app-f"])
        self.assertEqual(out["alias1.example.org"], [301])
        self.assertEqual(out["alias2.example.org"], [301])
        self.assertEqual(out["f.example.org"], [200])

    def test_non_string_entries_in_lists_are_dropped(self):
        apps = {"app-g": {}}
        self._configure_returns({
            ("app-g", "server.domains.canonical"): ["ok.g.example.org", None, 123, {"x": "y"}],
            ("app-g", "server.domains.aliases"):   [{"bad": "obj"}, "alias.g.example.org", None],
            ("app-g", "server.status_codes"):      {},  # → fallback
        })
        out = self.mod.web_health_expectations(apps, group_names=["app-g"])
        self.assertIn("ok.g.example.org", out)
        self.assertEqual(out["alias.g.example.org"], [301])
        self.assertNotIn(123, out)

    # ------------ WWW mapping (flag) --------------

    def test_www_mapping_is_added_and_forced_to_301_when_enabled(self):
        apps = {"app-h": {}}
        # includes a canonical that already starts with www.
        self._configure_returns({
            ("app-h", "server.domains.canonical"): ["h.example.org", "www.keep301.example.org"],
            ("app-h", "server.domains.aliases"):   ["alias.h.example.org"],
            ("app-h", "server.status_codes"):      {"default": 405},
        })
        out = self.mod.web_health_expectations(apps, group_names=["app-h"], www_enabled=True)

        # base domains
        self.assertEqual(out["h.example.org"], [405])
        self.assertEqual(out["alias.h.example.org"], [301])

        # auto-generated www.* entries always 301
        self.assertEqual(out["www.h.example.org"], [301])
        self.assertEqual(out["www.alias.h.example.org"], [301])

        # any pre-existing www.* must be forced to 301 too
        self.assertEqual(out["www.keep301.example.org"], [301])

    def test_no_www_mapping_when_disabled(self):
        apps = {"app-i": {}}
        self._configure_returns({
            ("app-i", "server.domains.canonical"): ["i.example.org"],
            ("app-i", "server.domains.aliases"):   [],
            ("app-i", "server.status_codes"):      {"default": 200},
        })
        out = self.mod.web_health_expectations(apps, group_names=["app-i"], www_enabled=False)
        self.assertIn("i.example.org", out)
        self.assertNotIn("www.i.example.org", out)

    # ------------ redirect_maps -------------------

    def test_redirect_maps_sources_are_included_as_301(self):
        apps = {}
        out = self.mod.web_health_expectations(
            apps,
            group_names=["any"],  # required, even if no apps
            redirect_maps=[{"source": "mail.example.org"}, "legacy.example.org"]
        )
        self.assertEqual(out["mail.example.org"], [301])
        self.assertEqual(out["legacy.example.org"], [301])

    def test_redirect_maps_override_app_expectations(self):
        apps = {"conflict-app": {}}
        self._configure_returns({
            ("conflict-app", "server.domains.canonical"): ["conflict.example.org"],
            ("conflict-app", "server.domains.aliases"):   [],
            ("conflict-app", "server.status_codes"):      {"default": 200},
        })
        out = self.mod.web_health_expectations(
            apps,
            group_names=["conflict-app"],
            redirect_maps=[{"source": "conflict.example.org"}]
        )
        self.assertEqual(out["conflict.example.org"], [301])

    def test_redirect_maps_get_www_when_enabled(self):
        apps = {}
        out = self.mod.web_health_expectations(
            apps,
            group_names=["any"],
            www_enabled=True,
            redirect_maps=[{"source": "redir.example.org"}]
        )
        self.assertEqual(out["redir.example.org"], [301])
        self.assertEqual(out["www.redir.example.org"], [301])

    def test_redirect_maps_independent_of_group_filter(self):
        apps = {"ignored-app": {}}
        self._configure_returns({
            ("ignored-app", "server.domains.canonical"): ["ignored.example.org"],
            ("ignored-app", "server.domains.aliases"):   [],
            ("ignored-app", "server.status_codes"):      {"default": 200},
        })
        out = self.mod.web_health_expectations(
            apps,
            group_names=["some-other-app"],  # excludes the only app
            redirect_maps=[{"source": "manual.example.org"}]
        )
        self.assertNotIn("ignored.example.org", out)
        self.assertEqual(out["manual.example.org"], [301])


if __name__ == "__main__":
    unittest.main()
