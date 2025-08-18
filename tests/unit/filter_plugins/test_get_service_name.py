import unittest
from filter_plugins import get_service_name

class TestGetServiceName(unittest.TestCase):
    def test_default_suffix_service(self):
        self.assertEqual(
            get_service_name.get_service_name("sys-ctl-cln-backups", "nginx"),
            "sys-ctl-cln-backups.nginx.service"
        )

    def test_default_suffix_timer(self):
        self.assertEqual(
            get_service_name.get_service_name("sys-ctl-bkp@", "postgres"),
            "sys-ctl-bkp.postgres@.timer"
        )

    def test_explicit_custom_suffix(self):
        self.assertEqual(
            get_service_name.get_service_name("sys-ctl-bkp@", "postgres", "special"),
            "sys-ctl-bkp.postgres@.special"
        )

    def test_explicit_false_suffix(self):
        self.assertEqual(
            get_service_name.get_service_name("sys-ctl-bkp@", "postgres", False),
            "sys-ctl-bkp.postgres@"
        )
        self.assertEqual(
            get_service_name.get_service_name("sys-ctl-cln-backups", "nginx", False),
            "sys-ctl-cln-backups.nginx"
        )

    def test_case_is_lowered(self):
        self.assertEqual(
            get_service_name.get_service_name("Sys-CTL-BKP@", "Postgres", "SeRviCe"),
            "sys-ctl-bkp.postgres@.service"
        )


if __name__ == "__main__":
    unittest.main()
