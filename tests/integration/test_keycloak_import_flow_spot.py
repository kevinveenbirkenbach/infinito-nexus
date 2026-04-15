import pathlib
import unittest


class TestKeycloakImportFlowSpot(unittest.TestCase):
    def test_keycloak_service_does_not_use_startup_import_flag(self):
        content = pathlib.Path(
            "roles/web-app-keycloak/templates/compose.yml.j2"
        ).read_text(encoding="utf-8")

        self.assertNotIn("--import-realm", content)
        self.assertIn("command: start", content)

    def test_keycloak_has_one_shot_realm_import_task(self):
        entry_content = pathlib.Path(
            "roles/web-app-keycloak/tasks/05_realm_import.yml"
        ).read_text(encoding="utf-8")
        run_content = pathlib.Path(
            "roles/web-app-keycloak/tasks/05a_realm_import_run.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("include_tasks: 05a_realm_import_run.yml", entry_content)
        self.assertIn("compose run --rm --no-deps", run_content)
        self.assertIn("--entrypoint /opt/keycloak/bin/kc.sh", run_content)
        self.assertIn("keycloak import --file", run_content)
        self.assertIn("KEYCLOAK_REALM_IMPORT_FILE_DOCKER", run_content)
        self.assertIn("include_tasks: 04_login.yml", run_content)

    def test_keycloak_resolves_realm_dictionary_at_task_runtime(self):
        content = pathlib.Path("roles/web-app-keycloak/tasks/03_init.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("KEYCLOAK_RESERVED_USERNAMES_LIST", content)
        self.assertIn("KEYCLOAK_DICTIONARY_REALM_RAW", content)
        self.assertIn("KEYCLOAK_USER_PROFILE_CONFIG_PAYLOAD", content)

    def test_keycloak_vars_use_runtime_application_lookup_for_redirects(self):
        content = pathlib.Path("roles/web-app-keycloak/vars/main.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("redirect_uris(lookup('applications')", content)
        self.assertIn("regex_replace('/+$', '')", content)

    def test_keycloak_provisions_realm_users_without_ldap(self):
        core_content = pathlib.Path(
            "roles/web-app-keycloak/tasks/01_core.yml"
        ).read_text(encoding="utf-8")
        user_sync_content = pathlib.Path(
            "roles/web-app-keycloak/tasks/update/08_users_realm.yml"
        ).read_text(encoding="utf-8")
        script_content = pathlib.Path(
            "roles/web-app-keycloak/files/ensure_realm_user.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("include_tasks: update/08_users_realm.yml", core_content)
        self.assertIn("when: not KEYCLOAK_LDAP_ENABLED | bool", core_content)
        self.assertIn("lookup('users', 'administrator').username", user_sync_content)
        self.assertIn("KEYCLOAK_LOCAL_REALM_ADMIN_PASSWORD", user_sync_content)
        self.assertIn('PASSWORD="$2"', script_content)
        self.assertIn('"${KEYCLOAK_PASSWORD}"', script_content)

    def test_keycloak_only_imports_and_keeps_ldap_federation_when_ldap_is_enabled(self):
        core_content = pathlib.Path(
            "roles/web-app-keycloak/tasks/01_core.yml"
        ).read_text(encoding="utf-8")
        import_content = pathlib.Path(
            "roles/web-app-keycloak/templates/import/realm.json.j2"
        ).read_text(encoding="utf-8")
        cleanup_content = pathlib.Path(
            "roles/web-app-keycloak/tasks/update/05_ldap_disabled.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("include_tasks: update/05_ldap_disabled.yml", core_content)
        self.assertIn("when: not KEYCLOAK_LDAP_ENABLED | bool", core_content)
        self.assertIn("{%- if KEYCLOAK_LDAP_ENABLED | bool -%}", import_content)
        self.assertIn(
            'include "components/org.keycloak.storage.UserStorageProvider.json.j2"',
            import_content,
        )
        self.assertIn("selectattr('providerId','equalto','ldap')", cleanup_content)
        self.assertIn("delete components/{{ item }}", cleanup_content)


if __name__ == "__main__":
    unittest.main()
