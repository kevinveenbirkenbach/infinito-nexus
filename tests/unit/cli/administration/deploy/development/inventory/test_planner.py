"""Unit tests for `cli.administration.deploy.development.inventory.planner`.

Covers:

* the default-mode `plan_dev_inventory_matrix` path (mocking
  legacy_resolver),
* `filter_plan_to_variant`,
* the variant-only mode gate (verifies that primaries with
  `meta/variants.yml` route through `variants.*` instead of
  `legacy_resolver.*`).
"""

from __future__ import annotations

import unittest
from typing import ClassVar
from unittest.mock import MagicMock, patch

from cli.administration.deploy.development.inventory import (
    filter_plan_to_variant,
    plan_dev_inventory_matrix,
)


class TestPlanDevInventoryMatrix(unittest.TestCase):
    @patch(
        "cli.administration.deploy.development.inventory.legacy_resolver._resolve_round_include",
        autospec=True,
    )
    @patch(
        "cli.administration.deploy.development.inventory.legacy_resolver._build_services_overrides_for_round",
        autospec=True,
        return_value={},
    )
    @patch(
        "cli.administration.deploy.development.inventory.planner.get_variants",
        autospec=True,
    )
    def test_single_variant_apps_share_one_unsuffixed_folder(
        self,
        get_variants_mock: MagicMock,
        _overrides_mock: MagicMock,
        resolve_include_mock: MagicMock,
    ) -> None:
        get_variants_mock.return_value = {
            "web-app-foo": [{}],
            "web-app-bar": [{}],
        }
        resolve_include_mock.return_value = ("web-app-foo", "web-app-bar")
        plan = plan_dev_inventory_matrix(
            roles_dir="/roles",
            primary_apps=["web-app-foo", "web-app-bar"],
            base_inventory_dir="/srv/inv",
        )
        self.assertEqual(
            plan,
            [
                (
                    0,
                    "/srv/inv",
                    {"web-app-foo": 0, "web-app-bar": 0},
                    ("web-app-foo", "web-app-bar"),
                )
            ],
        )

    @patch(
        "cli.administration.deploy.development.inventory.legacy_resolver._resolve_round_include",
        autospec=True,
    )
    @patch(
        "cli.administration.deploy.development.inventory.legacy_resolver._build_services_overrides_for_round",
        autospec=True,
        return_value={},
    )
    @patch(
        "cli.administration.deploy.development.inventory.planner.get_variants",
        autospec=True,
    )
    def test_two_variant_primary_drives_two_suffixed_folders(
        self,
        get_variants_mock: MagicMock,
        _overrides_mock: MagicMock,
        resolve_include_mock: MagicMock,
    ) -> None:
        get_variants_mock.return_value = {
            "web-app-multi": [{"variant": 0}, {"variant": 1}],
            "web-app-keycloak": [{}],
        }
        resolve_include_mock.side_effect = [
            ("web-app-multi", "web-app-keycloak"),
            ("web-app-multi", "web-app-keycloak"),
        ]
        plan = plan_dev_inventory_matrix(
            roles_dir="/roles",
            primary_apps=["web-app-multi"],
            base_inventory_dir="/srv/inv",
        )
        self.assertEqual(
            plan,
            [
                (
                    0,
                    "/srv/inv-0",
                    {"web-app-multi": 0, "web-app-keycloak": 0},
                    ("web-app-multi", "web-app-keycloak"),
                ),
                (
                    1,
                    "/srv/inv-1",
                    {"web-app-multi": 1, "web-app-keycloak": 0},
                    ("web-app-multi", "web-app-keycloak"),
                ),
            ],
        )

    @patch(
        "cli.administration.deploy.development.inventory.legacy_resolver._resolve_round_include",
        autospec=True,
    )
    @patch(
        "cli.administration.deploy.development.inventory.legacy_resolver._build_services_overrides_for_round",
        autospec=True,
        return_value={},
    )
    @patch(
        "cli.administration.deploy.development.inventory.planner.get_variants",
        autospec=True,
    )
    def test_round_count_driven_by_primary_max_variants(
        self,
        get_variants_mock: MagicMock,
        _overrides_mock: MagicMock,
        resolve_include_mock: MagicMock,
    ) -> None:
        # Both primaries; rounds = max(3, 2) = 3.
        get_variants_mock.return_value = {
            "web-app-three": [{}, {}, {}],
            "web-app-two": [{}, {}],
        }
        resolve_include_mock.side_effect = [
            ("web-app-three", "web-app-two"),
            ("web-app-three", "web-app-two"),
            ("web-app-three", "web-app-two"),
        ]
        plan = plan_dev_inventory_matrix(
            roles_dir="/roles",
            primary_apps=["web-app-three", "web-app-two"],
            base_inventory_dir="/srv/inv",
        )
        # Round 0,1,2 -> three has 0,1,2 / two has 0,1,0 (clamped on R=2).
        self.assertEqual(
            plan,
            [
                (
                    0,
                    "/srv/inv-0",
                    {"web-app-three": 0, "web-app-two": 0},
                    ("web-app-three", "web-app-two"),
                ),
                (
                    1,
                    "/srv/inv-1",
                    {"web-app-three": 1, "web-app-two": 1},
                    ("web-app-three", "web-app-two"),
                ),
                (
                    2,
                    "/srv/inv-2",
                    {"web-app-three": 2, "web-app-two": 0},
                    ("web-app-three", "web-app-two"),
                ),
            ],
        )

    def test_empty_primary_apps_rejected(self):
        with self.assertRaises(ValueError):
            plan_dev_inventory_matrix(
                roles_dir="/roles",
                primary_apps=[],
                base_inventory_dir="/srv/inv",
            )


class TestFilterPlanToVariant(unittest.TestCase):
    PLAN: ClassVar[list[tuple]] = [
        (
            0,
            "/srv/inv-0",
            {"web-app-multi": 0, "web-app-keycloak": 0},
            ("web-app-multi", "web-app-keycloak"),
        ),
        (
            1,
            "/srv/inv-1",
            {"web-app-multi": 1, "web-app-keycloak": 0},
            ("web-app-multi", "web-app-keycloak"),
        ),
    ]

    def test_none_returns_full_plan(self):
        self.assertEqual(filter_plan_to_variant(self.PLAN, None), self.PLAN)

    def test_pins_to_named_round(self):
        self.assertEqual(
            filter_plan_to_variant(self.PLAN, 1),
            [self.PLAN[1]],
        )

    def test_out_of_range_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "variant 7 out of range"):
            filter_plan_to_variant(self.PLAN, 7)


class TestPlanDevInventoryMatrixVariantOnlyGate(unittest.TestCase):
    @patch(
        "cli.administration.deploy.development.inventory.variants._topo_sort_by_run_after",
        autospec=True,
    )
    @patch(
        "cli.administration.deploy.development.inventory.variants._detect_variant_conflicts",
        autospec=True,
    )
    @patch(
        "cli.administration.deploy.development.inventory.variants._resolve_round_include_variant_only",
        autospec=True,
    )
    @patch(
        "cli.administration.deploy.development.inventory.legacy_resolver._resolve_round_include",
        autospec=True,
    )
    @patch(
        "cli.administration.deploy.development.inventory.variants._has_explicit_variants",
        autospec=True,
    )
    @patch(
        "cli.administration.deploy.development.inventory.planner.get_variants",
        autospec=True,
    )
    def test_variant_only_path_taken_when_primary_has_variants_yml(
        self,
        get_variants_mock: MagicMock,
        gate_mock: MagicMock,
        legacy_include_mock: MagicMock,
        variant_include_mock: MagicMock,
        conflict_mock: MagicMock,
        topo_mock: MagicMock,
    ) -> None:
        get_variants_mock.return_value = {"web-app-matomo": [{}]}
        gate_mock.return_value = True
        variant_include_mock.return_value = ("web-app-matomo",)
        topo_mock.return_value = ("web-app-matomo",)

        plan = plan_dev_inventory_matrix(
            roles_dir="/roles",
            primary_apps=["web-app-matomo"],
            base_inventory_dir="/srv/inv",
        )

        # Variant-only path used, legacy resolver untouched.
        variant_include_mock.assert_called_once()
        conflict_mock.assert_called_once()
        topo_mock.assert_called_once()
        legacy_include_mock.assert_not_called()
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0][3], ("web-app-matomo",))

    @patch(
        "cli.administration.deploy.development.inventory.legacy_resolver._build_services_overrides_for_round",
        autospec=True,
        return_value={},
    )
    @patch(
        "cli.administration.deploy.development.inventory.variants._resolve_round_include_variant_only",
        autospec=True,
    )
    @patch(
        "cli.administration.deploy.development.inventory.legacy_resolver._resolve_round_include",
        autospec=True,
    )
    @patch(
        "cli.administration.deploy.development.inventory.variants._has_explicit_variants",
        autospec=True,
        return_value=False,
    )
    @patch(
        "cli.administration.deploy.development.inventory.planner.get_variants",
        autospec=True,
    )
    def test_legacy_path_taken_when_no_primary_has_variants_yml(
        self,
        get_variants_mock: MagicMock,
        _gate_mock: MagicMock,
        legacy_include_mock: MagicMock,
        variant_include_mock: MagicMock,
        _overrides_mock: MagicMock,
    ) -> None:
        get_variants_mock.return_value = {"web-app-foo": [{}]}
        legacy_include_mock.return_value = ("web-app-foo",)

        plan = plan_dev_inventory_matrix(
            roles_dir="/roles",
            primary_apps=["web-app-foo"],
            base_inventory_dir="/srv/inv",
        )

        legacy_include_mock.assert_called_once()
        variant_include_mock.assert_not_called()
        self.assertEqual(plan[0][3], ("web-app-foo",))

    @patch(
        "cli.administration.deploy.development.inventory.variants._has_explicit_variants",
        autospec=True,
        return_value=True,
    )
    @patch(
        "cli.administration.deploy.development.inventory.planner.get_variants",
        autospec=True,
    )
    def test_variant_conflict_propagates_to_caller(
        self,
        get_variants_mock: MagicMock,
        _gate_mock: MagicMock,
    ) -> None:
        # Two primaries declaring the same key with disagreeing flags
        # MUST bubble up as a ValueError from the planner.
        get_variants_mock.return_value = {
            "web-app-matomo": [
                {"services": {"logout": {"enabled": True, "shared": True}}}
            ],
            "web-app-dashboard": [
                {"services": {"logout": {"enabled": False, "shared": False}}}
            ],
        }
        with (
            patch(
                "cli.administration.inventory.provision.services_disabler.find_provider_roles",
                autospec=True,
                return_value={"logout": "web-svc-logout"},
            ),
            self.assertRaisesRegex(ValueError, "Variant conflict at round 0"),
        ):
            plan_dev_inventory_matrix(
                roles_dir="/roles",
                primary_apps=["web-app-matomo", "web-app-dashboard"],
                base_inventory_dir="/srv/inv",
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
