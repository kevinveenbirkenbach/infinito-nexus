import unittest
from unittest.mock import patch

# Importiere das Filtermodul
# Pfad relativ zum Projekt; falls nötig, passe den Importpfad an
import importlib
jvm_filters = importlib.import_module("filter_plugins.jvm_filters")


class TestJvmFilters(unittest.TestCase):
    def setUp(self):
        # Dummy applications dict – Inhalt egal, da get_app_conf gemockt wird
        self.apps = {"whatever": True}
        self.app_id = "web-app-confluence"  # entity_name wird gemockt

    # -----------------------------
    # Helpers
    # -----------------------------
    def _with_conf(self, mem_limit: str, mem_res: str):
        """
        Context manager der get_app_conf/get_entity_name passend patched.
        """
        patches = [
            patch("filter_plugins.jvm_filters.get_entity_name", return_value="confluence"),
            patch(
                "filter_plugins.jvm_filters.get_app_conf",
                side_effect=lambda apps, app_id, key, required=True: (
                    mem_limit if key.endswith(".mem_limit")
                    else mem_res if key.endswith(".mem_reservation")
                    else None
                ),
            ),
        ]
        ctxs = [p.start() for p in patches]
        self.addCleanup(lambda: [p.stop() for p in patches])
        return ctxs

    # -----------------------------
    # Tests: jvm_max_mb / jvm_min_mb Sizing
    # -----------------------------
    def test_sizing_8g_limit_6g_reservation(self):
        # mem_limit=8g → candidates: 70% = 5734MB (floor 8*0.7=5.6GB→ 5734MB via int math 8*7//10=5)
        # int math: (8*1024)*7//10 = (8192)*7//10 = 5734
        # limit-1024 = 8192-1024 = 7168
        # 12288
        # → Xmx = min(5734, 7168, 12288) = 5734 → floor at 1024 keeps 5734
        # Xms = min(Xmx//2=2867, res=6144, Xmx=5734) = 2867 (>=512)
        self._with_conf("8g", "6g")
        xmx = jvm_filters.jvm_max_mb(self.apps, self.app_id)
        xms = jvm_filters.jvm_min_mb(self.apps, self.app_id)
        self.assertEqual(xmx, 5734)
        self.assertEqual(xms, 2867)

    def test_sizing_6g_limit_4g_reservation(self):
        # limit=6g → 70%: (6144*7)//10 = 4300, limit-1024=5120, 12288 → Xmx=4300
        # Xms=min(4300//2=2150, 4096, 4300)=2150
        self._with_conf("6g", "4g")
        xmx = jvm_filters.jvm_max_mb(self.apps, self.app_id)
        xms = jvm_filters.jvm_min_mb(self.apps, self.app_id)
        self.assertEqual(xmx, 4300)
        self.assertEqual(xms, 2150)

    def test_sizing_16g_limit_12g_reservation_cap_12288(self):
        # limit=16g → 70%: (16384*7)//10 = 11468, limit-1024=15360, cap=12288 → Xmx=min(11468,15360,12288)=11468
        # Xms=min(11468//2=5734, 12288 (12g), 11468) = 5734
        self._with_conf("16g", "12g")
        xmx = jvm_filters.jvm_max_mb(self.apps, self.app_id)
        xms = jvm_filters.jvm_min_mb(self.apps, self.app_id)
        self.assertEqual(xmx, 11468)
        self.assertEqual(xms, 5734)

    def test_floor_small_limit_results_in_min_1024(self):
        # limit=1g → 70%: 716, limit-1024=0, 12288 → min=0 → floor → 1024
        self._with_conf("1g", "512m")
        xmx = jvm_filters.jvm_max_mb(self.apps, self.app_id)
        self.assertEqual(xmx, 1024)

    def test_floor_small_reservation_results_in_min_512(self):
        # limit groß genug, aber reservation sehr klein → Xms floored to 512
        self._with_conf("4g", "128m")
        xms = jvm_filters.jvm_min_mb(self.apps, self.app_id)
        self.assertEqual(xms, 512)

    # -----------------------------
    # Tests: Fehlerfälle / Validierung
    # -----------------------------
    def test_invalid_unit_raises(self):
        with patch("filter_plugins.jvm_filters.get_entity_name", return_value="confluence"), \
             patch("filter_plugins.jvm_filters.get_app_conf", side_effect=lambda apps, app_id, key, required=True:
                   "8Q" if key.endswith(".mem_limit") else "4g"):
            with self.assertRaises(jvm_filters.AnsibleFilterError):
                jvm_filters.jvm_max_mb(self.apps, self.app_id)

    def test_zero_limit_raises(self):
        with patch("filter_plugins.jvm_filters.get_entity_name", return_value="confluence"), \
             patch("filter_plugins.jvm_filters.get_app_conf", side_effect=lambda apps, app_id, key, required=True:
                   "0" if key.endswith(".mem_limit") else "4g"):
            with self.assertRaises(jvm_filters.AnsibleFilterError):
                jvm_filters.jvm_max_mb(self.apps, self.app_id)

    def test_zero_reservation_raises(self):
        with patch("filter_plugins.jvm_filters.get_entity_name", return_value="confluence"), \
             patch("filter_plugins.jvm_filters.get_app_conf", side_effect=lambda apps, app_id, key, required=True:
                   "8g" if key.endswith(".mem_limit") else "0"):
            with self.assertRaises(jvm_filters.AnsibleFilterError):
                jvm_filters.jvm_min_mb(self.apps, self.app_id)

    def test_entity_name_is_derived_not_passed(self):
        # Sicherstellen, dass get_entity_name() aufgerufen wird und kein externer Parameter nötig ist
        with patch("filter_plugins.jvm_filters.get_entity_name", return_value="confluence") as mock_entity, \
             patch("filter_plugins.jvm_filters.get_app_conf", side_effect=lambda apps, app_id, key, required=True:
                   "8g" if key.endswith(".mem_limit") else "6g"):
            xmx = jvm_filters.jvm_max_mb(self.apps, self.app_id)
            xms = jvm_filters.jvm_min_mb(self.apps, self.app_id)
            self.assertGreater(xmx, 0)
            self.assertGreater(xms, 0)
            self.assertEqual(mock_entity.call_count, 3)
            for call in mock_entity.call_args_list:
                self.assertEqual(call.args[0], self.app_id)


if __name__ == "__main__":
    unittest.main()
