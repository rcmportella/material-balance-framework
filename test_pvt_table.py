import unittest

import numpy as np

from material_balance.PVT_table import build_opm_pvt_text, calculate_pvt_table
from material_balance.pvt_properties import CorrelationsPVT


class PVTTableTests(unittest.TestCase):
    def test_undersaturated_oil_viscosity_uses_beggs_robinson_extension(self):
        bubble_point_pressure = 140.0
        results = calculate_pvt_table(
            temperature_c=82.0,
            pressure_min=100.0,
            pressure_max=220.0,
            bubble_point_pressure=bubble_point_pressure,
            API=35.0,
            gamma_g=0.65,
            point_count=4,
        )

        bubble_index = np.flatnonzero(
            np.isclose(results["pressure"], bubble_point_pressure)
        )[0]
        mu_ob = CorrelationsPVT.oil_viscosity_beggs_robinson(
            35.0, 82.0, results["Rsb"][0] if "Rsb" in results else results["Rs"][bubble_index]
        )

        self.assertEqual(np.sum(np.isclose(results["pressure"], bubble_point_pressure)), 1)
        self.assertAlmostEqual(results["mu_o"][bubble_index], mu_ob)
        self.assertTrue(np.all(np.diff(results["mu_o"][bubble_index:]) > 0))

    def test_pvto_exports_only_the_last_undersaturated_pressure_without_rs(self):
        results = calculate_pvt_table(
            temperature_c=82.0,
            pressure_min=100.0,
            pressure_max=220.0,
            bubble_point_pressure=140.0,
            API=35.0,
            gamma_g=0.65,
            point_count=4,
        )

        pvto_text = build_opm_pvt_text(results, bubble_point_pressure=140.0, unit_system="METRIC")
        pvto_rows = [
            line for line in pvto_text.split("PVTO\n", maxsplit=1)[1].splitlines()
            if line and not line.startswith("--")
        ]
        undersaturated_rows = [line for line in pvto_rows if line.startswith("\t")]

        self.assertEqual(len(undersaturated_rows), 1)
        self.assertEqual(undersaturated_rows[0].split("\t")[0], "")
        self.assertTrue(undersaturated_rows[0].endswith("/"))


if __name__ == "__main__":
    unittest.main()