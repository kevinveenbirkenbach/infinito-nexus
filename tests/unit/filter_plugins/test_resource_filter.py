# tests/unit/filter_plugins/test_resource_filter.py
import unittest
from unittest.mock import patch

import importlib
plugin_module = importlib.import_module("filter_plugins.resource_filter")


class TestResourceFilter(unittest.TestCase):
    def setUp(self):
        importlib.reload(plugin_module)

        self.applications = {"some": "dict"}
        self.application_id = "web-app-foo"
        self.key = "cpus"

        # Patch get_app_conf und get_entity_name im Plugin
        self.patcher_conf = patch.object(plugin_module, "get_app_conf")
        self.patcher_entity = patch.object(plugin_module, "get_entity_name")
        self.mock_get_app_conf = self.patcher_conf.start()
        self.mock_get_entity_name = self.patcher_entity.start()
        self.mock_get_entity_name.return_value = "foo"  # abgeleiteter Service-Name

    def tearDown(self):
        self.patcher_conf.stop()
        self.patcher_entity.stop()

    def test_primary_service_value_found(self):
        # Primary liefert direkt einen Wert
        self.mock_get_app_conf.return_value = "0.75"

        result = plugin_module.resource_filter(
            self.applications,
            self.application_id,
            self.key,
            service_name="openresty",
            hard_default="0.5",
        )

        self.assertEqual(result, "0.75")
        self.mock_get_app_conf.assert_called_once_with(
            self.applications, "docker.services.openresty.cpus", False, None
        )

    def test_service_name_empty_uses_get_entity_name(self):
        # service_name == "" → get_entity_name(application_id) -> "foo"
        self.mock_get_app_conf.return_value = "1.0"

        result = plugin_module.resource_filter(
            self.applications,
            self.application_id,
            self.key,
            service_name="",
            hard_default="0.5",
        )

        self.assertEqual(result, "1.0")
        self.mock_get_entity_name.assert_called_once_with(self.application_id)
        self.mock_get_app_conf.assert_called_once_with(
            self.applications, "docker.services.foo.cpus", False, None
        )

    def test_returns_hard_default_when_missing(self):
        # Kein Wert im primary → verwende hard_default
        self.mock_get_app_conf.return_value = None

        result = plugin_module.resource_filter(
            self.applications,
            self.application_id,
            key="mem_limit",
            service_name="openresty",
            hard_default="2g",
        )

        self.assertEqual(result, "2g")
        self.mock_get_app_conf.assert_called_once_with(
            self.applications, "docker.services.openresty.mem_limit", False, None
        )

    def test_raises_ansible_filter_error_on_config_errors(self):
        self.mock_get_app_conf.side_effect = plugin_module.AppConfigKeyError("bad path")

        with self.assertRaises(plugin_module.AnsibleFilterError):
            plugin_module.resource_filter(
                self.applications,
                self.application_id,
                key="pids_limit",
                service_name="openresty",
                hard_default=2048,
            )


if __name__ == "__main__":
    unittest.main()
