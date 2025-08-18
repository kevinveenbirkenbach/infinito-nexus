import unittest
from filter_plugins import get_service_name

class TestGetServiceName(unittest.TestCase):
    def test_normal_service(self):
        # Expect a dot between id and software name
        self.assertEqual(
            get_service_name.get_service_name("sys-ctl-cln-backups", "nginx"),
            "sys-ctl-cln-backups.nginx.service"
        )

    def test_normal_service_custom_suffix(self):
        self.assertEqual(
            get_service_name.get_service_name("sys-ctl-cln-backups", "nginx", "timer"),
            "sys-ctl-cln-backups.nginx.timer"
        )

    def test_with_at_suffix(self):
        # If systemctl_id ends with '@', @ is moved behind software name
        self.assertEqual(
            get_service_name.get_service_name("sys-ctl-bkp@", "postgres"),
            "sys-ctl-bkp.postgres@.service"
        )

    def test_with_at_and_custom_suffix(self):
        self.assertEqual(
            get_service_name.get_service_name("sys-ctl-bkp@", "postgres", "timer"),
            "sys-ctl-bkp.postgres@.timer"
        )

    def test_case_is_lowered(self):
        self.assertEqual(
            get_service_name.get_service_name("Sys-CTL-BKP@", "Postgres", "SeRviCe"),
            "sys-ctl-bkp.postgres@.service"
        )


if __name__ == "__main__":
    unittest.main()
