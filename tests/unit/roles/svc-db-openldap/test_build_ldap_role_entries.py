import unittest
import os
import importlib.util

# Dynamisch den Filter-Plugin Pfad hinzufügen
current_dir = os.path.dirname(__file__)
filter_plugin_path = os.path.abspath(
    os.path.join(current_dir, "../../../../roles/svc-db-openldap/filter_plugins")
)

# Modul dynamisch laden
spec = importlib.util.spec_from_file_location(
    "build_ldap_role_entries",
    os.path.join(filter_plugin_path, "build_ldap_role_entries.py"),
)
ble_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ble_module)

build_ldap_role_entries = ble_module.build_ldap_role_entries


class TestBuildLdapRoleEntries(unittest.TestCase):
    def setUp(self):
        self.applications = {
            "app1": {
                "group_id": 10000,
                "rbac": {
                    "roles": {
                        "editor": {"description": "Can edit content"},
                        "viewer": {"description": "Can view content"},
                    }
                },
            }
        }

        self.users = {
            "alice": {"roles": ["editor", "administrator"]},
            "bob": {"roles": ["viewer"]},
            "carol": {"roles": []},
        }

        self.ldap = {
            "DN": {
                "OU": {
                    "USERS": "ou=users,dc=example,dc=org",
                    "ROLES": "ou=roles,dc=example,dc=org",
                }
            },
            "USER": {"ATTRIBUTES": {"ID": "uid"}},
            "RBAC": {"FLAVORS": ["posixGroup", "groupOfNames"]},
        }

    def test_entries_structure(self):
        entries = build_ldap_role_entries(self.applications, self.users, self.ldap)
        expected_dns = {
            "cn=app1-editor,ou=roles,dc=example,dc=org",
            "cn=app1-viewer,ou=roles,dc=example,dc=org",
            "cn=app1-administrator,ou=roles,dc=example,dc=org",
        }
        self.assertEqual(set(entries.keys()), expected_dns)

    def test_posix_group_members(self):
        entries = build_ldap_role_entries(self.applications, self.users, self.ldap)
        editor = entries["cn=app1-editor,ou=roles,dc=example,dc=org"]
        self.assertEqual(editor["gidNumber"], 10000)
        self.assertIn("memberUid", editor)
        self.assertIn("alice", editor["memberUid"])

    def test_group_of_names_members(self):
        entries = build_ldap_role_entries(self.applications, self.users, self.ldap)
        viewer = entries["cn=app1-viewer,ou=roles,dc=example,dc=org"]
        expected_dn = "uid=bob,ou=users,dc=example,dc=org"
        self.assertIn("member", viewer)
        self.assertIn(expected_dn, viewer["member"])

    def test_administrator_auto_included(self):
        entries = build_ldap_role_entries(self.applications, self.users, self.ldap)
        admin = entries["cn=app1-administrator,ou=roles,dc=example,dc=org"]
        self.assertEqual(
            admin["description"],
            "Has full administrative access: manage themes, plugins, settings, and users",
        )
        self.assertIn("alice", admin.get("memberUid", []))

    def test_empty_roles_are_skipped(self):
        entries = build_ldap_role_entries(self.applications, self.users, self.ldap)
        for entry in entries.values():
            if entry["cn"].endswith("-viewer"):
                self.assertNotIn("carol", entry.get("memberUid", []))


class TestBuildLdapRoleEntriesGroupNamesGate(unittest.TestCase):
    """Gate: only applications whose application_id appears in group_names
    contribute LDAP groups. When group_names is None, the gate is bypassed
    (backwards-compatible). See requirement 004 for rationale."""

    def setUp(self):
        self.applications = {
            "web-app-wordpress": {
                "group_id": 10001,
                "rbac": {
                    "roles": {
                        "editor": {"description": "Editor"},
                    }
                },
            },
            "web-app-pretix": {
                "group_id": 10002,
                "rbac": {
                    "roles": {
                        "organizer": {"description": "Organizer"},
                    }
                },
            },
        }
        self.users = {"alice": {"roles": ["editor"]}}
        self.ldap = {
            "DN": {
                "OU": {
                    "USERS": "ou=users,dc=example,dc=org",
                    "ROLES": "ou=roles,dc=example,dc=org",
                }
            },
            "USER": {"ATTRIBUTES": {"ID": "uid"}},
            "RBAC": {"FLAVORS": ["posixGroup"]},
        }

    def test_only_deployed_apps_contribute_when_group_names_given(self):
        entries = build_ldap_role_entries(
            self.applications,
            self.users,
            self.ldap,
            group_names=["web-app-wordpress"],
        )
        cns = {entry["cn"] for entry in entries.values()}
        # WordPress is in group_names → editor + administrator provisioned
        self.assertIn("web-app-wordpress-editor", cns)
        self.assertIn("web-app-wordpress-administrator", cns)
        # pretix is NOT in group_names → no groups for it
        self.assertNotIn("web-app-pretix-organizer", cns)
        self.assertNotIn("web-app-pretix-administrator", cns)

    def test_empty_group_names_emits_no_entries(self):
        entries = build_ldap_role_entries(
            self.applications,
            self.users,
            self.ldap,
            group_names=[],
        )
        self.assertEqual(entries, {})

    def test_group_names_none_preserves_legacy_behavior(self):
        entries = build_ldap_role_entries(
            self.applications,
            self.users,
            self.ldap,
            group_names=None,
        )
        cns = {entry["cn"] for entry in entries.values()}
        # Every app contributes when gate is off — matches pre-004 behavior.
        self.assertIn("web-app-wordpress-editor", cns)
        self.assertIn("web-app-pretix-organizer", cns)
        self.assertIn("web-app-wordpress-administrator", cns)
        self.assertIn("web-app-pretix-administrator", cns)

    def test_group_names_with_unknown_id_emits_no_entries(self):
        entries = build_ldap_role_entries(
            self.applications,
            self.users,
            self.ldap,
            group_names=["web-app-not-in-applications"],
        )
        self.assertEqual(entries, {})


if __name__ == "__main__":
    unittest.main()
