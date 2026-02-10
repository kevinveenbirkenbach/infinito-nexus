# tests/unit/filter_plugins/test_get_deployment_types_from_groups.py
from __future__ import annotations

from unittest import TestCase, main

from filter_plugins.get_deployment_types_from_groups import (
    get_deployment_types_from_groups,
)


class TestGetDeploymentTypesFromGroups(TestCase):
    def test_exact_types(self) -> None:
        self.assertEqual(
            get_deployment_types_from_groups(["server", "workstation"]),
            ["server", "workstation"],
        )

    def test_aliases(self) -> None:
        self.assertEqual(
            get_deployment_types_from_groups(["servers", "workstations"]),
            ["server", "workstation"],
        )

    def test_prefix_matches(self) -> None:
        self.assertEqual(
            get_deployment_types_from_groups(["server_ci", "workstation-build"]),
            ["server", "workstation"],
        )

    def test_universal_only(self) -> None:
        self.assertEqual(
            get_deployment_types_from_groups(["universal"]),
            ["universal"],
        )

    def test_none_or_empty(self) -> None:
        self.assertEqual(get_deployment_types_from_groups(None), [])
        self.assertEqual(get_deployment_types_from_groups([]), [])

    def test_irrelevant_groups(self) -> None:
        self.assertEqual(
            get_deployment_types_from_groups(["foo", "bar", "baz"]),
            [],
        )


if __name__ == "__main__":
    main()
