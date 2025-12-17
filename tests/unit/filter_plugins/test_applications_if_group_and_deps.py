import unittest
from unittest.mock import patch, mock_open

from ansible.errors import AnsibleFilterError

from filter_plugins.applications_if_group_and_deps import FilterModule


class TestApplicationsIfGroupAndDeps(unittest.TestCase):
    def setUp(self):
        self.filter = FilterModule()
        # minimal applications dict
        self.apps = {
            "app1": {"foo": "bar"},
            "app2": {"baz": "qux"},
            "roleA": {"some": "cfg"},
        }

    def test_invalid_inputs(self):
        with self.assertRaises(AnsibleFilterError):
            self.filter.applications_if_group_and_deps("not a dict", [])
        with self.assertRaises(AnsibleFilterError):
            self.filter.applications_if_group_and_deps({}, "not a list")

    def test_direct_inclusion(self):
        # if an app key is directly in group_names it should be returned
        groups = ["app1", "unrelated"]
        result = self.filter.applications_if_group_and_deps(self.apps, groups)
        self.assertEqual(set(result.keys()), {"app1"})

    @patch("filter_plugins.applications_if_group_and_deps.yaml.safe_load")
    @patch("filter_plugins.applications_if_group_and_deps.open", new_callable=mock_open)
    @patch("filter_plugins.applications_if_group_and_deps.os.path.isfile")
    def test_indirect_inclusion_via_dependencies(self, mock_isfile, mock_file, mock_yaml):
        """
        Simulate that group 'groupX' has a dependency on 'roleA', and that
        roleA's vars/main.yml contains application_id: 'roleA'.
        Then passing group_names=['groupX'] should include 'roleA'.
        """
        # pretend both meta/main.yml and vars/main.yml exist
        mock_isfile.return_value = True

        # safe_load() calls:
        # 1) groupX/meta/main.yml → dependencies ['roleA']
        # 2) roleA/meta/main.yml  → dependencies []
        # 3) roleA/vars/main.yml  → application_id 'roleA'
        mock_yaml.side_effect = [
            {"dependencies": ["roleA"]},
            {"dependencies": []},
            {"application_id": "roleA"},
        ]

        result = self.filter.applications_if_group_and_deps(self.apps, ["groupX"])
        self.assertEqual(set(result.keys()), {"roleA"})

    @patch("filter_plugins.applications_if_group_and_deps.yaml.safe_load")
    @patch("filter_plugins.applications_if_group_and_deps.open", new_callable=mock_open)
    @patch("filter_plugins.applications_if_group_and_deps.os.path.isfile")
    def test_no_vars_file(self, mock_isfile, mock_file, mock_yaml):
        """
        If a meta/main.yml dependency exists but vars/main.yml is missing,
        that role won't contribute an application_id, so nothing is returned.
        """
        # meta exists, vars does not
        def isfile_side(path: str) -> bool:
            return path.endswith("meta/main.yml")

        mock_isfile.side_effect = isfile_side

        # meta declares dependency
        mock_yaml.return_value = {"dependencies": ["roleA"]}

        result = self.filter.applications_if_group_and_deps(self.apps, ["groupX"])
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
