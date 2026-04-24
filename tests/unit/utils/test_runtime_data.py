from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from utils.runtime_data import (
    _build_users,
    _compute_reserved_usernames,
    _deep_merge,
    _fingerprint_mapping,
    _hydrate_users_tokens,
    _load_user_defs,
    _load_yaml_mapping,
    _materialize_builtin_user_aliases,
    _merge_users,
    _reset_cache_for_tests,
    _stable_variables_signature,
    get_application_defaults,
    get_user_defaults,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


class TestLoadYamlMapping(unittest.TestCase):
    def test_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_load_yaml_mapping(Path(tmp) / "missing.yml"), {})

    def test_empty_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.yml"
            path.write_text("", encoding="utf-8")
            self.assertEqual(_load_yaml_mapping(path), {})

    def test_non_mapping_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "list.yml"
            path.write_text("- a\n- b\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                _load_yaml_mapping(path)

    def test_mapping_returns_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ok.yml"
            path.write_text("foo: 1\nbar: [1, 2]\n", encoding="utf-8")
            self.assertEqual(_load_yaml_mapping(path), {"foo": 1, "bar": [1, 2]})


class TestDeepMerge(unittest.TestCase):
    def test_nested_merge(self):
        base = {"a": {"b": 1, "c": 2}, "keep": [1]}
        override = {"a": {"c": 99, "d": 3}, "new": "x"}
        merged = _deep_merge(base, override)
        self.assertEqual(
            merged,
            {"a": {"b": 1, "c": 99, "d": 3}, "keep": [1], "new": "x"},
        )

    def test_scalar_override_replaces_mapping(self):
        self.assertEqual(_deep_merge({"a": 1}, "x"), "x")

    def test_override_deepcopies(self):
        base = {}
        override = {"a": {"list": [1, 2]}}
        merged = _deep_merge(base, override)
        merged["a"]["list"].append(3)
        self.assertEqual(override["a"]["list"], [1, 2])


class TestMergeUsers(unittest.TestCase):
    def test_none_overrides_returns_defaults_copy(self):
        defaults = {"alice": {"uid": 1001}}
        merged = _merge_users(defaults, None)
        self.assertEqual(merged, defaults)
        merged["alice"]["uid"] = 0
        self.assertEqual(defaults["alice"]["uid"], 1001)

    def test_override_merges_per_user(self):
        defaults = {"alice": {"uid": 1001, "email": "a@x"}}
        overrides = {"alice": {"email": "new@x"}, "bob": {"uid": 2000}}
        merged = _merge_users(defaults, overrides)
        self.assertEqual(merged["alice"], {"uid": 1001, "email": "new@x"})
        self.assertEqual(merged["bob"], {"uid": 2000})


class TestComputeReservedUsernames(unittest.TestCase):
    def test_extracts_suffix_after_last_dash(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles = Path(tmp)
            (roles / "web-app-mailu").mkdir()
            (roles / "svc-db-postgres").mkdir()
            (roles / "sys-ctl-alm-email").mkdir()
            (roles / "not-a-dir.txt").write_text("", encoding="utf-8")

            self.assertEqual(
                _compute_reserved_usernames(roles),
                ["email", "mailu", "postgres"],
            )

    def test_ignores_non_alnum_or_non_lower(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles = Path(tmp)
            (roles / "web-app-Foo").mkdir()
            (roles / "weird-name_with_underscore").mkdir()
            (roles / "svc-db-pg").mkdir()

            self.assertEqual(_compute_reserved_usernames(roles), ["pg"])


class TestFingerprintMapping(unittest.TestCase):
    def setUp(self) -> None:
        _reset_cache_for_tests()

    def test_none_is_zero(self):
        self.assertEqual(_fingerprint_mapping(None), "0")

    def test_same_content_same_fingerprint(self):
        a = {"x": 1, "y": 2}
        b = {"y": 2, "x": 1}
        self.assertEqual(_fingerprint_mapping(a), _fingerprint_mapping(b))

    def test_different_content_different_fingerprint(self):
        a = {"x": 1}
        b = {"x": 2}
        self.assertNotEqual(_fingerprint_mapping(a), _fingerprint_mapping(b))

    def test_id_cache_short_circuits_recompute(self):
        obj = {"x": 1}
        first = _fingerprint_mapping(obj)
        obj["x"] = 999
        cached = _fingerprint_mapping(obj)
        self.assertEqual(first, cached)
        _reset_cache_for_tests()
        self.assertNotEqual(first, _fingerprint_mapping(obj))


class TestStableVariablesSignature(unittest.TestCase):
    def setUp(self) -> None:
        _reset_cache_for_tests()

    def test_empty_variables_returns_sentinel(self):
        self.assertEqual(_stable_variables_signature(None), ("0", "0", "", ""))
        self.assertEqual(_stable_variables_signature({}), ("0", "0", "", ""))

    def test_captures_key_subset(self):
        sig = _stable_variables_signature(
            {
                "applications": {"a": 1},
                "users": {"u": 2},
                "DOMAIN_PRIMARY": "example.com",
                "SYSTEM_EMAIL_DOMAIN": "mail.example.com",
                "irrelevant": "noise",
            }
        )
        self.assertEqual(sig[2], "example.com")
        self.assertEqual(sig[3], "mail.example.com")
        self.assertNotEqual(sig[0], "0")
        self.assertNotEqual(sig[1], "0")

    def test_signature_stable_across_identical_content(self):
        v1 = {"applications": {"a": 1}, "users": {"u": 2}}
        v2 = {"applications": {"a": 1}, "users": {"u": 2}}
        self.assertEqual(
            _stable_variables_signature(v1), _stable_variables_signature(v2)
        )


class TestLoadUserDefs(unittest.TestCase):
    def test_merges_non_conflicting_across_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles = Path(tmp)
            _write(
                roles / "role-a/users/main.yml",
                """
                users:
                  alice:
                    username: alice
                """,
            )
            _write(
                roles / "role-b/users/main.yml",
                """
                users:
                  alice:
                    email: alice@x
                  bob:
                    username: bob
                """,
            )
            defs = _load_user_defs(roles)
            self.assertEqual(defs["alice"], {"username": "alice", "email": "alice@x"})
            self.assertEqual(defs["bob"], {"username": "bob"})

    def test_conflicting_field_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles = Path(tmp)
            _write(
                roles / "role-a/users/main.yml",
                """
                users:
                  alice:
                    uid: 1001
                """,
            )
            _write(
                roles / "role-b/users/main.yml",
                """
                users:
                  alice:
                    uid: 2002
                """,
            )
            with self.assertRaisesRegex(ValueError, "Conflict for user 'alice'"):
                _load_user_defs(roles)

    def test_non_dict_user_entry_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles = Path(tmp)
            _write(
                roles / "role-a/users/main.yml",
                """
                users:
                  alice: "not-a-dict"
                """,
            )
            with self.assertRaisesRegex(ValueError, "Invalid definition"):
                _load_user_defs(roles)


class TestBuildUsers(unittest.TestCase):
    def _defs(self, mapping):
        from collections import OrderedDict

        return OrderedDict(mapping)

    def test_allocates_uids_starting_at_start_id(self):
        defs = self._defs([("alice", {}), ("bob", {})])
        users = _build_users(defs, "example.com", start_id=1001, become_pwd="pw")
        self.assertEqual(users["alice"]["uid"], 1001)
        self.assertEqual(users["bob"]["uid"], 1002)
        self.assertEqual(users["alice"]["gid"], 1001)

    def test_explicit_uid_preserved_allocator_skips(self):
        defs = self._defs(
            [("alice", {"uid": 1001}), ("bob", {}), ("carol", {"uid": 1002})]
        )
        users = _build_users(defs, "example.com", start_id=1001, become_pwd="pw")
        self.assertEqual(users["alice"]["uid"], 1001)
        self.assertEqual(users["bob"]["uid"], 1003)
        self.assertEqual(users["carol"]["uid"], 1002)

    def test_duplicate_explicit_uid_raises(self):
        defs = self._defs([("alice", {"uid": 1001}), ("bob", {"uid": 1001})])
        with self.assertRaisesRegex(ValueError, "Duplicate uid 1001"):
            _build_users(defs, "example.com", start_id=1001, become_pwd="pw")

    def test_duplicate_username_raises(self):
        defs = self._defs(
            [("alice", {"username": "shared"}), ("bob", {"username": "shared"})]
        )
        with self.assertRaisesRegex(ValueError, "Duplicate username 'shared'"):
            _build_users(defs, "example.com", start_id=1001, become_pwd="pw")

    def test_duplicate_email_raises(self):
        defs = self._defs(
            [
                ("alice", {"email": "same@x"}),
                ("bob", {"email": "same@x"}),
            ]
        )
        with self.assertRaisesRegex(ValueError, "Duplicate email 'same@x'"):
            _build_users(defs, "example.com", start_id=1001, become_pwd="pw")

    def test_defaults_fill_missing_fields(self):
        defs = self._defs([("alice", {})])
        users = _build_users(defs, "example.com", start_id=1001, become_pwd="pw")
        self.assertEqual(users["alice"]["username"], "alice")
        self.assertEqual(users["alice"]["email"], "alice@example.com")
        self.assertEqual(users["alice"]["password"], "pw")
        self.assertEqual(users["alice"]["firstname"], "alice")
        self.assertEqual(users["alice"]["lastname"], "example.com")


class TestHydrateUsersTokens(unittest.TestCase):
    def test_fills_only_missing_tokens(self):
        users = {
            "alice": {"tokens": {"app-a": "keep", "app-b": ""}},
            "bob": {"tokens": {}},
        }
        store = {
            "alice": {"tokens": {"app-a": "overwrite-attempt", "app-b": "fill"}},
            "bob": {"tokens": {"app-c": "fresh"}},
            "carol": {"tokens": {"app-d": "orphan"}},
        }
        hydrated = _hydrate_users_tokens(users, store)
        self.assertEqual(hydrated["alice"]["tokens"]["app-a"], "keep")
        self.assertEqual(hydrated["alice"]["tokens"]["app-b"], "fill")
        self.assertEqual(hydrated["bob"]["tokens"]["app-c"], "fresh")
        self.assertIn("carol", hydrated)
        self.assertEqual(hydrated["carol"]["tokens"]["app-d"], "orphan")

    def test_empty_store_is_passthrough(self):
        users = {"alice": {"tokens": {"a": "1"}}}
        self.assertEqual(_hydrate_users_tokens(users, None), users)
        self.assertEqual(_hydrate_users_tokens(users, {}), users)

    def test_does_not_mutate_input(self):
        users = {"alice": {"tokens": {}}}
        store = {"alice": {"tokens": {"x": "y"}}}
        _hydrate_users_tokens(users, store)
        self.assertEqual(users["alice"]["tokens"], {})


class TestMaterializeBuiltinUserAliases(unittest.TestCase):
    def test_rewrites_sld_and_tld_usernames(self):
        users = {
            "sld": {"username": "{{ DOMAIN_PRIMARY.split('.')[0] }}"},
            "tld": {"username": "{{ DOMAIN_PRIMARY.split('.')[1] }}"},
        }
        result = _materialize_builtin_user_aliases(
            users, {"DOMAIN_PRIMARY": "example.com"}
        )
        self.assertEqual(result["sld"]["username"], "example")
        self.assertEqual(result["tld"]["username"], "com")

    def test_no_domain_primary_is_passthrough(self):
        users = {"sld": {"username": "{{ DOMAIN_PRIMARY.split('.')[0] }}"}}
        result = _materialize_builtin_user_aliases(users, {})
        self.assertEqual(result, users)

    def test_non_placeholder_username_untouched(self):
        users = {"sld": {"username": "literal"}}
        result = _materialize_builtin_user_aliases(
            users, {"DOMAIN_PRIMARY": "example.com"}
        )
        self.assertEqual(result["sld"]["username"], "literal")


class TestGetApplicationDefaults(unittest.TestCase):
    def setUp(self) -> None:
        _reset_cache_for_tests()

    def tearDown(self) -> None:
        _reset_cache_for_tests()

    def test_reads_role_config_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles = Path(tmp)
            _write(
                roles / "web-app-alpha/config/main.yml",
                """
                server:
                  domains:
                    canonical:
                      - alpha.example
                """,
            )
            _write(
                roles / "web-app-beta/config/main.yml",
                """
                server:
                  domains:
                    canonical:
                      - beta.example
                """,
            )
            defaults = get_application_defaults(roles_dir=roles)
            self.assertEqual(sorted(defaults.keys()), ["web-app-alpha", "web-app-beta"])
            self.assertIn("group_id", defaults["web-app-alpha"])
            self.assertEqual(
                defaults["web-app-alpha"]["server"]["domains"]["canonical"],
                ["alpha.example"],
            )

    def test_wires_users_to_lookup_indirection(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles = Path(tmp)
            _write(
                roles / "web-app-alpha/config/main.yml",
                """
                server: {}
                """,
            )
            _write(
                roles / "web-app-alpha/users/main.yml",
                """
                users:
                  administrator:
                    username: administrator
                """,
            )
            defaults = get_application_defaults(roles_dir=roles)
            self.assertEqual(
                defaults["web-app-alpha"]["users"]["administrator"],
                "{{ lookup('users', 'administrator') }}",
            )

    def test_cache_returns_deep_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles = Path(tmp)
            _write(
                roles / "web-app-alpha/config/main.yml",
                """
                server:
                  domains:
                    canonical:
                      - alpha.example
                """,
            )
            first = get_application_defaults(roles_dir=roles)
            first["web-app-alpha"]["server"]["mutated"] = True
            second = get_application_defaults(roles_dir=roles)
            self.assertNotIn("mutated", second["web-app-alpha"]["server"])


class TestGetUserDefaults(unittest.TestCase):
    def setUp(self) -> None:
        _reset_cache_for_tests()

    def tearDown(self) -> None:
        _reset_cache_for_tests()

    def test_includes_role_defined_users(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles = Path(tmp)
            _write(
                roles / "web-app-alpha/users/main.yml",
                """
                users:
                  administrator:
                    username: administrator
                """,
            )
            users = get_user_defaults(roles_dir=roles)
            self.assertIn("administrator", users)
            self.assertEqual(users["administrator"]["uid"], 1001)

    def test_adds_reserved_users_from_role_suffixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles = Path(tmp)
            (roles / "svc-db-postgres").mkdir()
            (roles / "sys-ctl-alm-email").mkdir()
            users = get_user_defaults(roles_dir=roles)
            self.assertIn("postgres", users)
            self.assertTrue(users["postgres"]["reserved"])
            self.assertIn("email", users)
            self.assertTrue(users["email"]["reserved"])

    def test_cache_returns_deep_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            roles = Path(tmp)
            _write(
                roles / "web-app-alpha/users/main.yml",
                """
                users:
                  administrator:
                    username: administrator
                """,
            )
            first = get_user_defaults(roles_dir=roles)
            first["administrator"]["mutated"] = True
            second = get_user_defaults(roles_dir=roles)
            self.assertNotIn("mutated", second["administrator"])


if __name__ == "__main__":
    unittest.main()
