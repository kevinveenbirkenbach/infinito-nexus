import unittest
from unittest.mock import patch

from plugins.lookup import status
from plugins.lookup.status import LookupModule


class TestStatusLookup(unittest.TestCase):
    def setUp(self):
        status._reset_cache_for_tests()

    @patch("plugins.lookup.status.list_invokable_app_ids")
    def test_returns_dict_with_all_keys(self, mock_list):
        mock_list.return_value = ["web-app-friendica", "web-app-baserow"]
        result = LookupModule().run(
            [],
            variables={
                "APPLICATIONS_WHITELIST": ["web-app-friendica"],
                "group_names": ["web-app-friendica", "web-app-baserow"],
            },
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(
            set(result[0].keys()), {"whitelist", "running", "groups", "all"}
        )

    @patch("plugins.lookup.status.list_invokable_app_ids")
    def test_running_falls_back_to_groups_when_whitelist_empty(self, mock_list):
        mock_list.return_value = []
        result = LookupModule().run(
            [],
            variables={
                "APPLICATIONS_WHITELIST": [],
                "group_names": ["a", "b"],
            },
        )
        self.assertEqual(result[0]["running"], ["a", "b"])

    @patch("plugins.lookup.status.list_invokable_app_ids")
    def test_running_uses_whitelist_when_non_empty(self, mock_list):
        mock_list.return_value = []
        result = LookupModule().run(
            [],
            variables={
                "APPLICATIONS_WHITELIST": ["a"],
                "group_names": ["a", "b"],
            },
        )
        self.assertEqual(result[0]["running"], ["a"])

    @patch("plugins.lookup.status.list_invokable_app_ids")
    def test_whitelist_reflects_raw_input(self, mock_list):
        mock_list.return_value = []
        result = LookupModule().run(
            [],
            variables={
                "APPLICATIONS_WHITELIST": ["web-app-foo"],
                "group_names": ["web-app-bar"],
            },
        )
        # `whitelist` is the operator's raw input — no intersection with group.
        self.assertEqual(result[0]["whitelist"], ["web-app-foo"])

    @patch("plugins.lookup.status.list_invokable_app_ids")
    def test_groups_reflects_raw_input(self, mock_list):
        mock_list.return_value = []
        result = LookupModule().run(
            [],
            variables={
                "APPLICATIONS_WHITELIST": [],
                "group_names": ["a", "b", "c"],
            },
        )
        self.assertEqual(result[0]["groups"], ["a", "b", "c"])

    @patch("plugins.lookup.status.list_invokable_app_ids")
    def test_all_reflects_invokable_apps(self, mock_list):
        mock_list.return_value = ["x", "y", "z"]
        result = LookupModule().run([], variables={"group_names": []})
        self.assertEqual(result[0]["all"], ["x", "y", "z"])

    @patch("plugins.lookup.status.list_invokable_app_ids")
    def test_missing_vars_treated_as_empty(self, mock_list):
        mock_list.return_value = ["a"]
        result = LookupModule().run([], variables={})
        self.assertEqual(result[0]["whitelist"], [])
        self.assertEqual(result[0]["groups"], [])
        self.assertEqual(result[0]["running"], [])
        self.assertEqual(result[0]["all"], ["a"])

    @patch("plugins.lookup.status.list_invokable_app_ids")
    def test_caches_same_input(self, mock_list):
        mock_list.return_value = ["a"]
        LookupModule().run(
            [], variables={"APPLICATIONS_WHITELIST": [], "group_names": ["a"]}
        )
        LookupModule().run(
            [], variables={"APPLICATIONS_WHITELIST": [], "group_names": ["a"]}
        )
        # invokable lookup runs only once for identical (whitelist, group)
        self.assertEqual(mock_list.call_count, 1)


if __name__ == "__main__":
    unittest.main()
