import tempfile
import unittest
from pathlib import Path

import numpy as np

from material_balance.gas_pz_app import (
    ProductionHistory,
    calculate_pz_analysis,
    estimate_gp_at_pressure,
    read_production_csv,
)
from material_balance.pvt_properties import CorrelationsPVT


class GasPZAppTests(unittest.TestCase):
    def test_reads_metric_production_csv(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "production.csv"
            csv_path.write_text(
                "time,Gp,pressure\n0,0,225\n365,1000000,205\n",
                encoding="utf-8",
            )

            history = read_production_csv(csv_path)

        np.testing.assert_array_equal(history.time, [0, 365])
        np.testing.assert_array_equal(history.Gp, [0, 1_000_000])
        np.testing.assert_array_equal(history.pressure, [225, 205])

    def test_reads_semicolon_delimited_production_csv(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "production.csv"
            csv_path.write_text(
                "time;Gp;pressure\n"
                "0;0;226.55\n"
                "3031;1080000;205.85\n"
                "3079;3970000;201.49\n"
                "6382;194500000;158.84\n",
                encoding="utf-8",
            )

            history = read_production_csv(csv_path)

        self.assertEqual(len(history.time), 4)
        self.assertEqual(history.Gp[0], 0)
        self.assertEqual(history.Gp[-1], 194_500_000)
        self.assertEqual(history.pressure[-1], 158.84)

    def test_regression_recovers_known_giip(self):
        pressures = np.array([225.0, 205.7, 177.57, 149.44])
        temperature_c = 104.0
        gas_gravity = 0.65
        temperature_k = temperature_c + 273.15
        z_factor = np.array(
            [
                CorrelationsPVT.gas_z_factor_hall_yarborough(
                    pressure, temperature_k, gas_gravity
                )
                for pressure in pressures
            ]
        )
        pz = pressures / z_factor
        known_giip = 50_000_000.0
        gp = known_giip * (1.0 - pz / pz[0])
        history = ProductionHistory(
            time=np.array([0, 365, 730, 1095], dtype=float),
            Gp=gp,
            pressure=pressures,
        )

        result = calculate_pz_analysis(history, temperature_c, gas_gravity)

        self.assertAlmostEqual(result.giip, known_giip, delta=known_giip * 1e-10)
        self.assertAlmostEqual(result.r_squared, 1.0)
        np.testing.assert_allclose(result.z_factor, z_factor)

    def test_estimates_cumulative_production_at_final_pressure(self):
        pressures = np.array([225.0, 205.7, 177.57, 149.44])
        temperature_c = 104.0
        gas_gravity = 0.65
        temperature_k = temperature_c + 273.15
        z_factor = np.array(
            [
                CorrelationsPVT.gas_z_factor_hall_yarborough(
                    pressure, temperature_k, gas_gravity
                )
                for pressure in pressures
            ]
        )
        pz = pressures / z_factor
        known_giip = 50_000_000.0
        gp = known_giip * (1.0 - pz / pz[0])
        history = ProductionHistory(
            time=np.array([0, 365, 730, 1095], dtype=float),
            Gp=gp,
            pressure=pressures,
        )
        analysis = calculate_pz_analysis(history, temperature_c, gas_gravity)
        final_pressure = 130.0
        final_z = CorrelationsPVT.gas_z_factor_hall_yarborough(
            final_pressure, temperature_k, gas_gravity
        )
        expected_gp = (
            final_pressure / final_z - analysis.intercept
        ) / analysis.slope

        result_gp = estimate_gp_at_pressure(
            analysis, final_pressure, temperature_c, gas_gravity
        )

        self.assertAlmostEqual(result_gp, expected_gp)
        self.assertGreater(result_gp, history.Gp[-1])

    def test_rejects_final_pressure_above_initial_pressure(self):
        pressures = np.array([225.0, 205.0, 180.0])
        temperature_c = 104.0
        gas_gravity = 0.65
        temperature_k = temperature_c + 273.15
        z_factor = np.array(
            [
                CorrelationsPVT.gas_z_factor_hall_yarborough(
                    pressure, temperature_k, gas_gravity
                )
                for pressure in pressures
            ]
        )
        pz = pressures / z_factor
        gp = 10_000_000.0 * (1.0 - pz / pz[0])
        history = ProductionHistory(
            time=np.array([0, 365, 730], dtype=float),
            Gp=gp,
            pressure=pressures,
        )
        analysis = calculate_pz_analysis(history, temperature_c, gas_gravity)

        with self.assertRaisesRegex(ValueError, "must not exceed the initial"):
            estimate_gp_at_pressure(analysis, 230.0, temperature_c, gas_gravity)

    def test_rejects_csv_without_initial_zero_production_row(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "production.csv"
            csv_path.write_text(
                "time,Gp,pressure\n365,1000000,205\n730,2000000,180\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "first row must have Gp = 0"):
                read_production_csv(csv_path)


if __name__ == "__main__":
    unittest.main()