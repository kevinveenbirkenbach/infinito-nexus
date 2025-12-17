# tests/unit/roles/web-svc-logout/filter_plugins/test_domain_filters.py

import os
import unittest
import importlib.util

# Directory of this test file: .../tests/unit/roles/web-svc-logout/filter_plugins
THIS_DIR = os.path.dirname(__file__)

# Compute the repo root by going up five levels: tests → unit → roles → web-svc-logout → filter_plugins → repo root
REPO_ROOT = os.path.abspath(os.path.join(THIS_DIR, "../../../../.."))

# Path to the actual plugin under roles/web-svc-logout/filter_plugins
DOMAIN_FILTERS_PATH = os.path.join(
    REPO_ROOT, "roles", "web-svc-logout", "filter_plugins", "domain_filters.py"
)

# Dynamically load the domain_filters module
spec = importlib.util.spec_from_file_location("domain_filters", DOMAIN_FILTERS_PATH)
domain_filters = importlib.util.module_from_spec(spec)
spec.loader.exec_module(domain_filters)
FilterModule = domain_filters.FilterModule


class TestLogoutDomainsFilter(unittest.TestCase):
    def setUp(self):
        self.filter_fn = FilterModule().filters()["logout_domains"]

    def test_flatten_and_feature_flag(self):
        applications = {
            "app1": {
                "server": {"domains": {"canonical": "single.domain.com"}},
                "features": {"logout": True},
            },
            "app2": {
                "server": {"domains": {"canonical": ["list1.com", "list2.com"]}},
                "features": {"logout": True},
            },
            "app3": {
                "server": {
                    "domains": {"canonical": {"k1": "dictA.com", "k2": "dictB.com"}}
                },
                "features": {"logout": True},
            },
            "app4": {
                "server": {"domains": {"canonical": "no-logout.com"}},
                "features": {"logout": False},
            },
            "other": {
                "server": {"domains": {"canonical": "ignored.com"}},
                "features": {"logout": True},
            },
        }
        group_names = ["app1", "app2", "app3", "app4"]
        result = set(self.filter_fn(applications, group_names))
        expected = {
            "single.domain.com",
            "list1.com",
            "list2.com",
            "dictA.com",
            "dictB.com",
        }
        self.assertEqual(result, expected)

    def test_missing_canonical_defaults_empty(self):
        applications = {
            "app1": {
                "server": {"domains": {}},  # no 'canonical' key
                "features": {"logout": True},
            }
        }
        group_names = ["app1"]
        self.assertEqual(self.filter_fn(applications, group_names), [])

    def test_app_not_in_group(self):
        applications = {
            "app1": {
                "server": {"domains": {"canonical": "domain.com"}},
                "features": {"logout": True},
            }
        }
        group_names = []
        self.assertEqual(self.filter_fn(applications, group_names), [])

    def test_invalid_domain_type(self):
        applications = {
            "app1": {
                "server": {"domains": {"canonical": 123}},
                "features": {"logout": True},
            }
        }
        group_names = ["app1"]
        self.assertEqual(self.filter_fn(applications, group_names), [123])


if __name__ == "__main__":
    unittest.main()
