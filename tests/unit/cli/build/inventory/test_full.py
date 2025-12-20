import unittest
import os
import importlib.util
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../'))
SCRIPT_PATH = os.path.join(PROJECT_ROOT, 'cli', 'build', 'inventory', 'full/__main__.py')
spec = importlib.util.spec_from_file_location('full', SCRIPT_PATH)
full = importlib.util.module_from_spec(spec)
spec.loader.exec_module(full)

class TestFullInventoryScript(unittest.TestCase):

    def test_build_group_inventory(self):
        apps = ['app1', 'app2']
        host = 'myhost'
        inventory = full.build_group_inventory(apps, host)
        self.assertIn('all', inventory)
        self.assertIn('app1', inventory)
        self.assertIn('app2', inventory)
        self.assertEqual(inventory['app1'], {'hosts': [host]})
        self.assertEqual(inventory['all']['hosts'], [host])
        self.assertIn('app1', inventory['all']['children'])

    def test_build_hostvar_inventory(self):
        apps = ['foo', 'bar']
        host = 'testhost'
        inventory = full.build_hostvar_inventory(apps, host)
        self.assertIn('all', inventory)
        self.assertIn('_meta', inventory)
        self.assertIn('hostvars', inventory['_meta'])
        self.assertEqual(inventory['_meta']['hostvars'][host]['invokable_applications'], apps)
        self.assertEqual(inventory['all']['hosts'], [host])

    def test_ignore_filtering(self):
        # Simulate argument parsing logic for ignore flattening
        ignore_args = ['foo,bar', 'baz']
        ignore_ids = set()
        for entry in ignore_args:
            ignore_ids.update(i.strip() for i in entry.split(',') if i.strip())
        self.assertEqual(ignore_ids, {'foo', 'bar', 'baz'})

        # Filtering list
        apps = ['foo', 'bar', 'baz', 'other']
        filtered = [app for app in apps if app not in ignore_ids]
        self.assertEqual(filtered, ['other'])

    def test_ignore_filtering_empty(self):
        ignore_args = []
        ignore_ids = set()
        for entry in ignore_args:
            ignore_ids.update(i.strip() for i in entry.split(',') if i.strip())
        apps = ['a', 'b']
        filtered = [app for app in apps if app not in ignore_ids]
        self.assertEqual(filtered, ['a', 'b'])

if __name__ == '__main__':
    unittest.main()
