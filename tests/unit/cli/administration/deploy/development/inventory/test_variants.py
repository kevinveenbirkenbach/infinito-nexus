"""Unit tests for `cli.administration.deploy.development.inventory.variants`.

Covers the strict variant-only include resolver, the conflict detector,
the run_after topo-sort helper, and the small variant-block utilities.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from cli.administration.deploy.development.inventory import (
    _detect_variant_conflicts,
    _has_explicit_variants,
    _resolve_round_include_variant_only,
    _service_keys_with_enabled_and_shared,
    _topo_sort_by_run_after,
)


class TestHasExplicitVariants(unittest.TestCase):
    def test_returns_true_when_variants_file_present(self) -> None:
        with patch.object(Path, "is_file", return_value=True):
            self.assertTrue(_has_explicit_variants("web-app-matomo", "/roles"))

    def test_returns_false_when_file_missing(self) -> None:
        with patch.object(Path, "is_file", return_value=False):
            self.assertFalse(_has_explicit_variants("web-app-foo", "/roles"))


class TestServiceKeysWithEnabledAndShared(unittest.TestCase):
    def test_returns_keys_with_both_literal_true(self) -> None:
        merged = {
            "dashboard": {"enabled": True, "shared": True},
            "logout": {"enabled": True, "shared": True},
            "mariadb": {"enabled": True, "shared": False},
            "prometheus": {"enabled": False, "shared": True},
        }
        self.assertEqual(
            sorted(_service_keys_with_enabled_and_shared(merged)),
            ["dashboard", "logout"],
        )

    def test_skips_jinja_strings(self) -> None:
        merged = {
            "logout": {
                "enabled": "{{ 'web-svc-logout' in group_names }}",
                "shared": "{{ 'web-svc-logout' in group_names }}",
            },
            "matomo": {"enabled": True, "shared": True},
        }
        self.assertEqual(_service_keys_with_enabled_and_shared(merged), ["matomo"])

    def test_skips_non_mapping_entries(self) -> None:
        merged = {
            "weird-leaf": "just-a-string",
            "matomo": {"enabled": True, "shared": True},
        }
        self.assertEqual(_service_keys_with_enabled_and_shared(merged), ["matomo"])

    def test_handles_non_mapping_input(self) -> None:
        self.assertEqual(_service_keys_with_enabled_and_shared(None), [])
        self.assertEqual(_service_keys_with_enabled_and_shared("x"), [])


class TestResolveRoundIncludeVariantOnly(unittest.TestCase):
    @patch(
        "cli.administration.inventory.provision.services_disabler.find_provider_roles",
        autospec=True,
    )
    def test_primary_only_when_variant_has_no_eligible_keys(
        self, find_provider_mock: MagicMock
    ) -> None:
        # All keys disabled → no expansion. Primary stays as the only entry.
        variants = {
            "web-app-matomo": [
                {
                    "services": {
                        "dashboard": {"enabled": False, "shared": False},
                        "logout": {"enabled": False, "shared": False},
                    }
                }
            ],
        }
        include = _resolve_round_include_variant_only(
            primary_apps=["web-app-matomo"],
            round_index=0,
            variants_per_app=variants,
            roles_dir=Path("/roles"),
        )
        self.assertEqual(include, ("web-app-matomo",))
        find_provider_mock.assert_not_called()

    @patch(
        "cli.administration.inventory.provision.services_disabler.find_provider_roles",
        autospec=True,
    )
    def test_pulls_in_provider_roles_for_eligible_keys(
        self, find_provider_mock: MagicMock
    ) -> None:
        variants = {
            "web-app-matomo": [
                {
                    "services": {
                        "dashboard": {"enabled": True, "shared": True},
                        "logout": {"enabled": True, "shared": True},
                        "mariadb": {"enabled": True, "shared": False},
                    }
                }
            ],
        }
        find_provider_mock.return_value = {
            "dashboard": "web-app-dashboard",
            "logout": "web-svc-logout",
        }
        include = _resolve_round_include_variant_only(
            primary_apps=["web-app-matomo"],
            round_index=0,
            variants_per_app=variants,
            roles_dir=Path("/roles"),
        )
        # Primary first, then declared siblings in stable order.
        self.assertEqual(
            include,
            ("web-app-matomo", "web-app-dashboard", "web-svc-logout"),
        )
        # mariadb (shared=False) MUST NOT be in the lookup batch.
        called_keys = sorted(find_provider_mock.call_args.args[0])
        self.assertEqual(called_keys, ["dashboard", "logout"])

    @patch(
        "cli.administration.inventory.provision.services_disabler.find_provider_roles",
        autospec=True,
    )
    def test_self_reference_is_deduplicated(
        self, find_provider_mock: MagicMock
    ) -> None:
        variants = {
            "web-app-matomo": [
                {"services": {"matomo": {"enabled": True, "shared": True}}}
            ],
        }
        find_provider_mock.return_value = {"matomo": "web-app-matomo"}
        include = _resolve_round_include_variant_only(
            primary_apps=["web-app-matomo"],
            round_index=0,
            variants_per_app=variants,
            roles_dir=Path("/roles"),
        )
        self.assertEqual(include, ("web-app-matomo",))

    @patch(
        "cli.administration.inventory.provision.services_disabler.find_provider_roles",
        autospec=True,
    )
    def test_multiple_primaries_combine_siblings(
        self, find_provider_mock: MagicMock
    ) -> None:
        variants = {
            "web-app-matomo": [
                {"services": {"logout": {"enabled": True, "shared": True}}}
            ],
            "web-app-dashboard": [
                {"services": {"cdn": {"enabled": True, "shared": True}}}
            ],
        }
        find_provider_mock.side_effect = [
            {"logout": "web-svc-logout"},
            {"cdn": "web-svc-cdn"},
        ]
        include = _resolve_round_include_variant_only(
            primary_apps=["web-app-matomo", "web-app-dashboard"],
            round_index=0,
            variants_per_app=variants,
            roles_dir=Path("/roles"),
        )
        self.assertEqual(
            include,
            (
                "web-app-matomo",
                "web-svc-logout",
                "web-app-dashboard",
                "web-svc-cdn",
            ),
        )

    @patch(
        "cli.administration.inventory.provision.services_disabler.find_provider_roles",
        autospec=True,
    )
    def test_unknown_service_keys_are_silently_skipped(
        self, find_provider_mock: MagicMock
    ) -> None:
        variants = {
            "web-app-matomo": [
                {"services": {"no-such-service": {"enabled": True, "shared": True}}}
            ],
        }
        find_provider_mock.return_value = {}  # nothing resolves
        include = _resolve_round_include_variant_only(
            primary_apps=["web-app-matomo"],
            round_index=0,
            variants_per_app=variants,
            roles_dir=Path("/roles"),
        )
        self.assertEqual(include, ("web-app-matomo",))

    @patch(
        "cli.administration.inventory.provision.services_disabler.find_provider_roles",
        autospec=True,
    )
    def test_round_index_clamps_to_zero_when_out_of_range(
        self, find_provider_mock: MagicMock
    ) -> None:
        # 2 variants, asked for round 7 → clamp to 0.
        variants = {
            "web-app-matomo": [
                {"services": {"logout": {"enabled": True, "shared": True}}},
                {"services": {"logout": {"enabled": False, "shared": False}}},
            ],
        }
        find_provider_mock.return_value = {"logout": "web-svc-logout"}
        include = _resolve_round_include_variant_only(
            primary_apps=["web-app-matomo"],
            round_index=7,
            variants_per_app=variants,
            roles_dir=Path("/roles"),
        )
        # Variant 0's eligible keys win.
        self.assertEqual(include, ("web-app-matomo", "web-svc-logout"))


class TestDetectVariantConflicts(unittest.TestCase):
    def test_no_conflict_when_only_one_app(self) -> None:
        variants = {
            "web-app-matomo": [
                {"services": {"logout": {"enabled": True, "shared": True}}}
            ]
        }
        _detect_variant_conflicts(
            include=["web-app-matomo"],
            round_index=0,
            variants_per_app=variants,
        )  # MUST NOT raise

    def test_no_conflict_when_keys_do_not_overlap(self) -> None:
        variants = {
            "web-app-matomo": [
                {"services": {"logout": {"enabled": True, "shared": True}}}
            ],
            "web-app-dashboard": [
                {"services": {"cdn": {"enabled": True, "shared": True}}}
            ],
        }
        _detect_variant_conflicts(
            include=["web-app-matomo", "web-app-dashboard"],
            round_index=0,
            variants_per_app=variants,
        )  # MUST NOT raise

    def test_no_conflict_when_overlapping_keys_agree(self) -> None:
        variants = {
            "web-app-matomo": [
                {"services": {"logout": {"enabled": True, "shared": True}}}
            ],
            "web-app-dashboard": [
                {"services": {"logout": {"enabled": True, "shared": True}}}
            ],
        }
        _detect_variant_conflicts(
            include=["web-app-matomo", "web-app-dashboard"],
            round_index=0,
            variants_per_app=variants,
        )  # MUST NOT raise

    def test_raises_on_disagreement(self) -> None:
        variants = {
            "web-app-matomo": [
                {"services": {"logout": {"enabled": True, "shared": True}}}
            ],
            "web-app-dashboard": [
                {"services": {"logout": {"enabled": False, "shared": False}}}
            ],
        }
        with self.assertRaises(ValueError) as ctx:
            _detect_variant_conflicts(
                include=["web-app-matomo", "web-app-dashboard"],
                round_index=0,
                variants_per_app=variants,
            )
        msg = str(ctx.exception)
        self.assertIn("Variant conflict at round 0", msg)
        self.assertIn("logout", msg)
        self.assertIn("web-app-matomo", msg)
        self.assertIn("web-app-dashboard", msg)

    def test_jinja_string_vs_literal_true_is_a_conflict(self) -> None:
        variants = {
            "web-app-matomo": [
                {"services": {"logout": {"enabled": True, "shared": True}}}
            ],
            "web-app-dashboard": [
                {
                    "services": {
                        "logout": {
                            "enabled": "{{ 'web-svc-logout' in group_names }}",
                            "shared": "{{ 'web-svc-logout' in group_names }}",
                        }
                    }
                }
            ],
        }
        with self.assertRaises(ValueError):
            _detect_variant_conflicts(
                include=["web-app-matomo", "web-app-dashboard"],
                round_index=0,
                variants_per_app=variants,
            )


class TestTopoSortByRunAfter(unittest.TestCase):
    def test_empty_include_returns_empty(self) -> None:
        self.assertEqual(_topo_sort_by_run_after([], Path("/roles")), ())

    @patch(
        "utils.roles.meta_lookup.get_role_run_after",
        autospec=True,
        return_value=[],
    )
    def test_no_deps_preserves_input_order(self, _ra_mock: MagicMock) -> None:
        got = _topo_sort_by_run_after(["b", "a", "c"], Path("/roles"))
        self.assertEqual(got, ("b", "a", "c"))

    @patch("utils.roles.meta_lookup.get_role_run_after", autospec=True)
    def test_linear_chain_orders_deps_first(self, ra_mock: MagicMock) -> None:
        # c depends on b, b depends on a → order: a, b, c
        def side_effect(_role_dir, role_name):
            return {
                "a": [],
                "b": ["a"],
                "c": ["b"],
            }[role_name]

        ra_mock.side_effect = side_effect
        got = _topo_sort_by_run_after(["c", "b", "a"], Path("/roles"))
        self.assertEqual(got, ("a", "b", "c"))

    @patch("utils.roles.meta_lookup.get_role_run_after", autospec=True)
    def test_cycle_falls_back_to_input_order(self, ra_mock: MagicMock) -> None:
        # a → b → a (cycle): preserve declaration order
        def side_effect(_role_dir, role_name):
            return {"a": ["b"], "b": ["a"]}[role_name]

        ra_mock.side_effect = side_effect
        got = _topo_sort_by_run_after(["a", "b"], Path("/roles"))
        self.assertEqual(got, ("a", "b"))

    @patch("utils.roles.meta_lookup.get_role_run_after", autospec=True)
    def test_edges_outside_include_are_dropped(self, ra_mock: MagicMock) -> None:
        # b depends on z, but z is NOT in include → edge dropped.
        def side_effect(_role_dir, role_name):
            return {"a": [], "b": ["z"]}[role_name]

        ra_mock.side_effect = side_effect
        got = _topo_sort_by_run_after(["a", "b"], Path("/roles"))
        self.assertEqual(got, ("a", "b"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
