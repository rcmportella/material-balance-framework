import unittest
from datetime import datetime

from examples.plota_producao_pocos import build_opm_wconprod_text


class WconprodExportTests(unittest.TestCase):
    def test_formats_only_positive_orat_and_grat_monthly_records(self):
        wells = {
            "FU-016D": {
                "date": [datetime(2026, 1, 1), datetime(2026, 3, 1)],
                "Qgm": [20.0, 30.0],
                "Qwm": [0.0, 0.0],
                "Qom": [10.0, 0.0],
                "Qclm": [0.0, 0.0],
                "Qwim": [0.0, 0.0],
                "Qgim": [0.0, 0.0],
            }
        }

        exported = build_opm_wconprod_text(wells)

        self.assertIn(" 1 'JAN' 2026 /", exported)
        self.assertIn(" 'FU-016D' 'OPEN' 'ORAT' 10 1* 1* 2* 50 /", exported)
        self.assertIn(" 1 'FEB' 2026 /", exported)
        self.assertNotIn("'SHUT'", exported)
        self.assertIn(" 1 'MAR' 2026 /", exported)
        self.assertIn(" 'FU-016D' 'OPEN' 'GRAT' 1* 1* 30 2* 50 /", exported)
        self.assertEqual(exported.count("WCONPROD"), 2)

    def test_truncates_well_names_to_eight_characters(self):
        wells = {
            "FU-016D-EXT": {
                "date": [datetime(2026, 1, 1)],
                "Qgm": [0.0],
                "Qwm": [0.0],
                "Qom": [10.0],
                "Qclm": [0.0],
                "Qwim": [0.0],
                "Qgim": [0.0],
            }
        }

        exported = build_opm_wconprod_text(wells)

        self.assertIn(" 'FU-016D-' 'OPEN' 'ORAT' 10 1* 1* 2* 50 /", exported)

    def test_exports_only_positive_water_and_gas_injection_rates(self):
        wells = {
            "INJ-GAS-01": {
                "date": [datetime(2026, 1, 1), datetime(2026, 2, 1)],
                "Qgm": [0.0, 0.0],
                "Qwm": [0.0, 0.0],
                "Qom": [0.0, 0.0],
                "Qclm": [0.0, 0.0],
                "Qwim": [0.0, 0.0],
                "Qgim": [125.0, 0.0],
            },
            "INJ-WAT-01": {
                "date": [datetime(2026, 1, 1), datetime(2026, 2, 1)],
                "Qgm": [0.0, 0.0],
                "Qwm": [0.0, 0.0],
                "Qom": [0.0, 0.0],
                "Qclm": [0.0, 0.0],
                "Qwim": [0.0, 80.0],
                "Qgim": [0.0, 0.0],
            },
        }

        exported = build_opm_wconprod_text(wells)

        self.assertIn(" 'INJ-GAS-' 'GAS' 'OPEN' 'RATE' 125 1* 210 /", exported)
        self.assertIn(" 'INJ-WAT-' 'WAT' 'OPEN' 'RATE' 80 1* 210 /", exported)
        self.assertEqual(exported.count("WCONINJE"), 2)
        self.assertNotIn(" 'INJ-GAS-' 'GAS' 'OPEN' 'RATE' 0", exported)
        self.assertNotIn(" 'INJ-WAT-' 'WAT' 'OPEN' 'RATE' 0", exported)

    def test_exports_multiple_selected_producers_in_the_same_wconprod_block(self):
        wells = {
            "FU-016D": {
                "date": [datetime(2026, 1, 1)],
                "Qgm": [0.0], "Qwm": [0.0], "Qom": [10.0], "Qclm": [0.0], "Qwim": [0.0], "Qgim": [0.0],
            },
            "FU-017D": {
                "date": [datetime(2026, 1, 1)],
                "Qgm": [20.0], "Qwm": [0.0], "Qom": [0.0], "Qclm": [0.0], "Qwim": [0.0], "Qgim": [0.0],
            },
        }

        exported = build_opm_wconprod_text(wells)

        self.assertEqual(exported.count("WCONPROD"), 1)
        self.assertIn(" 'FU-016D' 'OPEN' 'ORAT' 10 1* 1* 2* 50 /", exported)
        self.assertIn(" 'FU-017D' 'OPEN' 'GRAT' 1* 1* 20 2* 50 /", exported)

    def test_warns_and_omits_wconinje_when_there_is_no_injection(self):
        wells = {
            "FU-016D": {
                "date": [datetime(2026, 1, 1)],
                "Qgm": [20.0],
                "Qwm": [0.0],
                "Qom": [10.0],
                "Qclm": [0.0],
                "Qwim": [0.0],
                "Qgim": [0.0],
            }
        }

        with self.assertWarnsRegex(UserWarning, "No water or gas injection rates"):
            exported = build_opm_wconprod_text(wells)

        self.assertNotIn("WCONINJE", exported)


if __name__ == "__main__":
    unittest.main()