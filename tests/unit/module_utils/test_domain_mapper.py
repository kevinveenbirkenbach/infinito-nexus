import sys
import unittest

from ansible.errors import AnsibleError

# Make "ansible.module_utils.domain_mapper" importable during plain unit tests.
import module_utils.domain_mapper as _domain_mapper

sys.modules.setdefault("ansible.module_utils.domain_mapper", _domain_mapper)


class TestDomainMapper(unittest.TestCase):
    def setUp(self):
        # A realistic applications mapping with varying shapes:
        self.applications = {
            "web-app-a": {
                "server": {
                    "domains": {
                        "canonical": ["a.example"],
                        "aliases": ["www.a.example", "A.ALIAS.EXAMPLE"],
                    }
                }
            },
            "web-app-b": {
                "server": {
                    "domains": {
                        # canonical as string
                        "canonical": "b.example",
                        # aliases empty list
                        "aliases": [],
                    }
                }
            },
            "web-app-c": {
                "server": {
                    "domains": {
                        # canonical as dict (variants)
                        "canonical": {"web": "c.example", "api": "api.c.example"},
                        # aliases as dict (variants)
                        "aliases": {"www": "www.c.example"},
                    }
                }
            },
            "web-app-nested": {
                "server": {
                    "domains": {
                        # nested shapes should flatten fine
                        "canonical": {
                            "web": ["nested.example", "NESTED2.example"],
                            "api": {"v1": "api.nested.example"},
                        },
                        "aliases": [
                            {"alt": "alt.nested.example"},
                            ["ALT2.nested.example", {"deep": ["deep.nested.example"]}],
                        ],
                    }
                }
            },
            # invalid/missing structures: should just yield nothing in iter_app_domains
            "web-app-no-server": {},
            "web-app-server-not-dict": {"server": "nope"},
            "web-app-domains-not-dict": {"server": {"domains": "nope"}},
        }

    def test_iter_app_domains_empty_on_invalid_structure(self):
        self.assertEqual(
            list(
                _domain_mapper.iter_app_domains(self.applications["web-app-no-server"])
            ),
            [],
        )
        self.assertEqual(
            list(
                _domain_mapper.iter_app_domains(
                    self.applications["web-app-server-not-dict"]
                )
            ),
            [],
        )
        self.assertEqual(
            list(
                _domain_mapper.iter_app_domains(
                    self.applications["web-app-domains-not-dict"]
                )
            ),
            [],
        )

    def test_iter_app_domains_flattens_all_supported_shapes(self):
        # web-app-a: list + list
        got_a = list(_domain_mapper.iter_app_domains(self.applications["web-app-a"]))
        self.assertEqual(
            got_a,
            ["a.example", "www.a.example", "A.ALIAS.EXAMPLE"],
        )

        # web-app-b: canonical str + aliases []
        got_b = list(_domain_mapper.iter_app_domains(self.applications["web-app-b"]))
        self.assertEqual(got_b, ["b.example"])

        # web-app-c: canonical dict + aliases dict
        got_c = list(_domain_mapper.iter_app_domains(self.applications["web-app-c"]))
        self.assertEqual(got_c, ["c.example", "api.c.example", "www.c.example"])

        # web-app-nested: nested list/dict combinations
        got_nested = list(
            _domain_mapper.iter_app_domains(self.applications["web-app-nested"])
        )
        self.assertEqual(
            got_nested,
            [
                "nested.example",
                "NESTED2.example",
                "api.nested.example",
                "alt.nested.example",
                "ALT2.nested.example",
                "deep.nested.example",
            ],
        )

    def test_build_domain_index_case_insensitive(self):
        idx = _domain_mapper.build_domain_index(self.applications)

        # Ensure normalized keys exist
        self.assertEqual(idx["a.example"], "web-app-a")
        self.assertEqual(idx["www.a.example"], "web-app-a")
        self.assertEqual(idx["a.alias.example"], "web-app-a")  # from "A.ALIAS.EXAMPLE"

        self.assertEqual(idx["b.example"], "web-app-b")
        self.assertEqual(idx["c.example"], "web-app-c")
        self.assertEqual(idx["api.c.example"], "web-app-c")
        self.assertEqual(idx["www.c.example"], "web-app-c")

        self.assertEqual(idx["nested.example"], "web-app-nested")
        self.assertEqual(idx["nested2.example"], "web-app-nested")
        self.assertEqual(idx["api.nested.example"], "web-app-nested")
        self.assertEqual(idx["alt.nested.example"], "web-app-nested")
        self.assertEqual(idx["alt2.nested.example"], "web-app-nested")
        self.assertEqual(idx["deep.nested.example"], "web-app-nested")

    def test_build_domain_index_type_check(self):
        with self.assertRaises(AnsibleError):
            _domain_mapper.build_domain_index("nope")  # type: ignore[arg-type]

    def test_build_domain_index_detects_collision_case_insensitive(self):
        apps = {
            "app1": {
                "server": {"domains": {"canonical": ["X.EXAMPLE"], "aliases": []}}
            },
            "app2": {
                "server": {"domains": {"canonical": ["x.example"], "aliases": []}}
            },
        }
        with self.assertRaises(AnsibleError) as ctx:
            _domain_mapper.build_domain_index(apps)
        self.assertIn("domain collision", str(ctx.exception).lower())

    def test_resolve_app_id_for_domain_found(self):
        self.assertEqual(
            _domain_mapper.resolve_app_id_for_domain(self.applications, "a.example"),
            "web-app-a",
        )
        self.assertEqual(
            _domain_mapper.resolve_app_id_for_domain(
                self.applications, "WWW.A.EXAMPLE"
            ),
            "web-app-a",
        )
        self.assertEqual(
            _domain_mapper.resolve_app_id_for_domain(
                self.applications, "api.c.example"
            ),
            "web-app-c",
        )
        self.assertEqual(
            _domain_mapper.resolve_app_id_for_domain(
                self.applications, "DEEP.NESTED.EXAMPLE"
            ),
            "web-app-nested",
        )

    def test_resolve_app_id_for_domain_not_found_or_empty(self):
        self.assertIsNone(
            _domain_mapper.resolve_app_id_for_domain(
                self.applications, "missing.example"
            )
        )
        self.assertIsNone(
            _domain_mapper.resolve_app_id_for_domain(self.applications, "")
        )
        self.assertIsNone(
            _domain_mapper.resolve_app_id_for_domain(self.applications, "   ")
        )
        self.assertIsNone(
            _domain_mapper.resolve_app_id_for_domain(self.applications, None)  # type: ignore[arg-type]
        )

    def test_resolve_app_id_for_domain_raises_on_collision(self):
        apps = {
            "app1": {
                "server": {"domains": {"canonical": ["x.example"], "aliases": []}}
            },
            "app2": {
                "server": {"domains": {"canonical": ["X.EXAMPLE"], "aliases": []}}
            },
        }
        with self.assertRaises(AnsibleError):
            _domain_mapper.resolve_app_id_for_domain(apps, "x.example")


if __name__ == "__main__":
    unittest.main()
