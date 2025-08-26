import os
import yaml
import unittest
from filter_plugins.applications_if_group_and_deps import FilterModule


def load_vars(role_name):
    # locate project root relative to this test file
    tests_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(tests_dir, '..', '..', '..'))
    vars_path = os.path.join(project_root, 'roles', role_name, 'vars', 'main.yml')
    with open(vars_path) as f:
        data = yaml.safe_load(f) or {}
    return data


class TestApplicationsIfGroupAndDeps(unittest.TestCase):
    def setUp(self):
        self.filter = FilterModule().applications_if_group_and_deps
        self.sample_apps = {
            'web-svc-html': {},
            'web-svc-legal': {},
            'web-svc-file': {},
            'web-svc-asset': {},
            'web-app-desktop': {},
            'util-srv-corporate-identity': {},
        }

    def test_direct_group(self):
        result = self.filter(self.sample_apps, ['web-svc-html'])
        self.assertIn('web-svc-html', result)
        self.assertNotIn('web-svc-legal', result)

    def test_recursive_deps(self):
        # html -> depends on none, but util-srv-corporate-identity pulls in web-svc-legal -> web-svc-html -> legal
        result = self.filter(self.sample_apps, ['util-srv-corporate-identity'])
        self.assertIn('util-srv-corporate-identity', result)
        self.assertIn('web-svc-legal', result)  # via web-svc-legal
        self.assertIn('web-svc-html', result)   # via web-svc-legal -> html

    def test_real_vars_files(self):
        # load real vars to get application_id
        corp_vars = load_vars('util-srv-corporate-identity')
        asset_vars = load_vars('web-svc-asset')
        # ensure IDs exist
        self.assertIn('application_id', corp_vars)
        self.assertIn('application_id', asset_vars)
        # run filter
        result = self.filter(self.sample_apps, ['util-srv-corporate-identity'])
        # ids from vars should appear
        self.assertIn(corp_vars['application_id'], result)
        self.assertIn(asset_vars['application_id'], result)


if __name__ == '__main__':
    unittest.main()
