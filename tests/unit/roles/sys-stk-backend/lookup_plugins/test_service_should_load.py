import importlib.util
import unittest
from pathlib import Path

from ansible.errors import AnsibleError


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _load_module(rel_path: str, name: str):
    path = _repo_root() / rel_path
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class TestServiceShouldLoadLookup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module(
            "roles/sys-stk-backend/lookup_plugins/service_should_load.py",
            "service_should_load",
        )

    def setUp(self):
        self.applications = {
            "web-app-test": {
                "compose": {
                    "services": {
                        "ldap": {"enabled": True, "shared": True},
                        "ollama": {"enabled": True, "shared": False},
                    }
                }
            }
        }

    def test_true_when_enabled_shared_not_run_once_and_not_self(self):
        result = self.mod.LookupModule().run(
            ["svc-db-openldap"],
            variables={
                "applications": self.applications,
                "application_id": "web-app-test",
                "service_name": "ldap",
            },
        )
        self.assertEqual(result, [True])

    def test_false_when_run_once_already_defined(self):
        result = self.mod.LookupModule().run(
            ["svc-db-openldap"],
            variables={
                "applications": self.applications,
                "application_id": "web-app-test",
                "service_name": "ldap",
                "run_once_svc_db_openldap": True,
            },
        )
        self.assertEqual(result, [False])

    def test_false_when_not_shared(self):
        result = self.mod.LookupModule().run(
            ["svc-ai-ollama"],
            variables={
                "applications": self.applications,
                "application_id": "web-app-test",
                "service_name": "ollama",
            },
        )
        self.assertEqual(result, [False])

    def test_false_when_application_equals_service(self):
        result = self.mod.LookupModule().run(
            ["web-app-test"],
            variables={
                "applications": self.applications,
                "application_id": "web-app-test",
                "service_name": "ldap",
            },
        )
        self.assertEqual(result, [False])

    def test_raises_when_service_id_is_empty(self):
        with self.assertRaises(AnsibleError):
            self.mod.LookupModule().run(
                ["   "],
                variables={
                    "applications": self.applications,
                    "application_id": "web-app-test",
                    "service_name": "ldap",
                },
            )

    def test_raises_when_applications_missing(self):
        with self.assertRaises(AnsibleError):
            self.mod.LookupModule().run(
                ["svc-db-openldap"],
                variables={"application_id": "web-app-test", "service_name": "ldap"},
            )


if __name__ == "__main__":
    unittest.main()
