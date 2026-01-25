import unittest

from ansible.errors import AnsibleFilterError

from filter_plugins.service_load_enabled import service_load_enabled


class TestServiceLoadEnabled(unittest.TestCase):
    def test_service_load_enabled_true_when_enabled_and_shared_true(self):
        applications = {
            "web-app-xwiki": {
                "docker": {
                    "services": {
                        "ldap": {
                            "enabled": True,
                            "shared": True,
                        }
                    }
                }
            }
        }

        self.assertTrue(service_load_enabled(applications, "web-app-xwiki", "ldap"))

    def test_service_load_enabled_false_when_shared_false(self):
        applications = {
            "web-app-xwiki": {
                "docker": {
                    "services": {
                        "ldap": {
                            "enabled": True,
                            "shared": False,
                        }
                    }
                }
            }
        }

        self.assertFalse(service_load_enabled(applications, "web-app-xwiki", "ldap"))

    def test_service_load_enabled_false_when_enabled_false(self):
        applications = {
            "web-app-xwiki": {
                "docker": {
                    "services": {
                        "ldap": {
                            "enabled": False,
                            "shared": True,
                        }
                    }
                }
            }
        }

        self.assertFalse(service_load_enabled(applications, "web-app-xwiki", "ldap"))

    def test_service_load_enabled_false_when_keys_missing(self):
        applications = {
            "web-app-xwiki": {
                "docker": {
                    "services": {
                        "ldap": {
                            # enabled/shared missing
                        }
                    }
                }
            }
        }

        self.assertFalse(service_load_enabled(applications, "web-app-xwiki", "ldap"))

    def test_service_load_enabled_uses_default_when_keys_missing(self):
        applications = {
            "web-app-xwiki": {
                "docker": {
                    "services": {
                        "ldap": {
                            # enabled/shared missing
                        }
                    }
                }
            }
        }

        self.assertTrue(
            service_load_enabled(applications, "web-app-xwiki", "ldap", default=True)
        )

    def test_service_load_enabled_missing_service_returns_false(self):
        applications = {
            "web-app-xwiki": {
                "docker": {
                    "services": {
                        # ldap missing entirely
                    }
                }
            }
        }

        self.assertFalse(service_load_enabled(applications, "web-app-xwiki", "ldap"))

    def test_service_load_enabled_missing_app_raises(self):
        applications = {"web-app-xwiki": {"docker": {"services": {}}}}

        with self.assertRaises(AnsibleFilterError):
            service_load_enabled(applications, "web-app-mediawiki", "ldap")


if __name__ == "__main__":
    unittest.main()
