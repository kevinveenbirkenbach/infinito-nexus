import unittest
import importlib.util
import os

TEST_DIR = os.path.dirname(__file__)
PLUGIN_PATH = os.path.abspath(os.path.join(
    TEST_DIR,
    '../../../../../roles/sys-ctl-bkp-docker-2-loc/filter_plugins/find_dock_val_by_bkp_entr.py'
))

spec = importlib.util.spec_from_file_location("find_dock_val_by_bkp_entr", PLUGIN_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
find_dock_val_by_bkp_entr = mod.find_dock_val_by_bkp_entr

class TestFindDockValByBkpEntr(unittest.TestCase):

    def setUp(self):
        self.applications = {
            'app1': {
                'docker': {
                    'services': {
                        'svc1': {
                            'name': 'svc1',
                            'image': 'nginx:latest',
                            'custom_field': 'foo',
                            'backup': {
                                'enabled': True,
                                'mode': 'full'
                            }
                        },
                        'svc2': {
                            'name': 'svc2',
                            'image': 'redis:alpine',
                            'custom_field': 'bar',
                            'backup': {
                                'enabled': False,
                            }
                        },
                        'svc3': {
                            'name': 'svc3',
                            'image': 'postgres:alpine'
                        }
                    }
                }
            },
            'app2': {
                'docker': {
                    'services': {
                        'svcA': {
                            'name': 'svcA',
                            'image': 'alpine:latest',
                            'backup': {
                                'enabled': 1,
                                'mode': 'diff'
                            }
                        },
                        'svcB': {
                            'name': 'svcB',
                            'image': 'ubuntu:latest',
                            'backup': {
                                'something_else': True,
                            }
                        }
                    }
                }
            },
            'app_no_docker': {
                'meta': 'should be skipped'
            }
        }

    def test_finds_services_with_enabled_backup_name(self):
        # Sucht alle service-namen, wo backup.enabled truthy ist
        result = find_dock_val_by_bkp_entr(self.applications, 'enabled', 'name')
        self.assertIn('svc1', result)
        self.assertIn('svcA', result)
        self.assertNotIn('svc2', result)
        self.assertNotIn('svc3', result)
        self.assertEqual(set(result), {'svc1', 'svcA'})

    def test_finds_services_with_enabled_backup_image(self):
        # Sucht alle image, wo backup.enabled truthy ist
        result = find_dock_val_by_bkp_entr(self.applications, 'enabled', 'image')
        self.assertIn('nginx:latest', result)
        self.assertIn('alpine:latest', result)
        self.assertNotIn('redis:alpine', result)
        self.assertNotIn('postgres:alpine', result)
        self.assertEqual(set(result), {'nginx:latest', 'alpine:latest'})

    def test_finds_services_with_enabled_backup_custom_field(self):
        # Sucht alle custom_field, wo backup.enabled truthy ist
        result = find_dock_val_by_bkp_entr(self.applications, 'enabled', 'custom_field')
        self.assertIn('foo', result)
        # svcA hat kein custom_field -> sollte nicht im Resultat sein
        self.assertEqual(result, ['foo'])

    def test_finds_other_backup_keys(self):
        # Sucht nach services, wo backup.mode gesetzt ist
        result = find_dock_val_by_bkp_entr(self.applications, 'mode', 'name')
        self.assertIn('svc1', result)
        self.assertIn('svcA', result)
        self.assertEqual(set(result), {'svc1', 'svcA'})

    def test_returns_empty_list_when_no_match(self):
        # Sucht nach services, wo backup.xyz nicht gesetzt ist
        result = find_dock_val_by_bkp_entr(self.applications, 'doesnotexist', 'name')
        self.assertEqual(result, [])

    def test_returns_empty_list_on_empty_input(self):
        result = find_dock_val_by_bkp_entr({}, 'enabled', 'name')
        self.assertEqual(result, [])

    def test_raises_on_non_dict_input(self):
        with self.assertRaises(Exception):
            find_dock_val_by_bkp_entr(None, 'enabled', 'name')
        with self.assertRaises(Exception):
            find_dock_val_by_bkp_entr([], 'enabled', 'name')

    def test_works_with_missing_field(self):
        # mapped_entry fehlt -> kein Eintrag im Ergebnis
        apps = {
            'a': {'docker': {'services': {'x': {'backup': {'enabled': True}}}}}
        }
        result = find_dock_val_by_bkp_entr(apps, 'enabled', 'foo')
        self.assertEqual(result, [])

    def test_works_with_multiple_matches(self):
        # Zwei Treffer, beide mit enabled, mit custom Rückgabefeld
        apps = {
            'a': {'docker': {'services': {
                'x': {'backup': {'enabled': True}, 'any': 'n1'},
                'y': {'backup': {'enabled': True}, 'any': 'n2'}
            }}}
        }
        result = find_dock_val_by_bkp_entr(apps, 'enabled', 'any')
        self.assertEqual(set(result), {'n1', 'n2'})

if __name__ == '__main__':
    unittest.main()
