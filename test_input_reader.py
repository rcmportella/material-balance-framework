import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from openpyxl import Workbook

from material_balance.input_reader import InputReader
from material_balance.oil_material_balance_app import (
    calculate_oil_material_balance,
    export_analysis_csv,
    material_balance_plot_data,
)
from material_balance.units import UnitSystem


class OilMaterialBalanceFileInputTests(unittest.TestCase):
    def test_plot_data_uses_eo_plus_m_eg_and_field_withdrawal_units(self):
        reservoir = SimpleNamespace(
            unit_system=UnitSystem.FIELD,
            m=0.5,
            Eo_values=[0.1, float('nan'), 0.2],
            Eg_values=[0.4, 0.5, 0.6],
            Efw_values=[0.3, 0.1, 0.2],
            F_values=[3, 4, 5],
        )

        x_values, f_values = material_balance_plot_data(reservoir)

        self.assertEqual(len(x_values), 2)
        self.assertAlmostEqual(x_values[0], 0.6)
        self.assertAlmostEqual(x_values[1], 0.7)
        self.assertAlmostEqual(f_values[0], 3 * 6.28981)
        self.assertAlmostEqual(f_values[1], 5 * 6.28981)

    def test_exports_results_in_field_units_when_configured(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / 'results.csv'
            production = SimpleNamespace(
                time=[10], pressure=[100], Np=[10], Gp=[2], Wp=[5]
            )
            reservoir = SimpleNamespace(
                unit_system=UnitSystem.FIELD,
                m=0.5, Eo_values=[0.1], Eg_values=[0.2], Efw_values=[0.3],
                Et_values=[0.6], F_values=[3],
            )

            export_analysis_csv(str(output_path), production, reservoir, [1000])

            with output_path.open(newline='', encoding='utf-8-sig') as result_file:
                rows = list(csv.reader(result_file))

        self.assertEqual(rows[0], [
            'time_days', 'pressure_psia', 'Np_STB', 'Gp_SCF', 'Wp_STB',
            'Eo', 'Eg', 'mEg', 'Eo_plus_mEg', 'Efw', 'Et', 'F_rb', 'STOIIP_STB',
        ])
        self.assertAlmostEqual(float(rows[1][1]), 100 * 14.2233)
        self.assertAlmostEqual(float(rows[1][2]), 10 * 6.28981)
        self.assertAlmostEqual(float(rows[1][3]), 2 * 35.3147)
        self.assertAlmostEqual(float(rows[1][4]), 5 * 6.28981)
        self.assertAlmostEqual(float(rows[1][11]), 3 * 6.28981)
        self.assertAlmostEqual(float(rows[1][12]), 1000 * 6.28981)

    def test_loads_pvt_and_production_data_with_gui_reservoir_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pvt_path = root / 'pvt_table.xlsx'
            workbook = Workbook()
            pvt_sheet = workbook.active
            pvt_sheet.title = 'PVT'
            pvt_sheet.append([
                'Pressão (bar)', 'Bo (m³/m³)', 'Bg (m³/m³)', 'Rs (m³/m³)',
                'Z', 'co (1/bar)', 'mu_g (cP)', 'mu_o (cP)',
            ])
            pvt_sheet.append([200, 1.20, 0.005, 90, 0.9, 0.001, 0.02, 1.5])
            pvt_sheet.append([180, 1.22, 0.0055, 80, 0.88, 0.001, 0.02, 1.6])
            pvt_sheet.append([160, 1.25, 0.006, 70, 0.86, 0.001, 0.02, 1.7])
            parameters = workbook.create_sheet('Parâmetros')
            parameters.append(['Parâmetro', 'Valor'])
            parameters.append(['Sistema de unidades', 'METRIC'])
            workbook.save(pvt_path)

            pvt = InputReader.read_pvt_from_file(str(pvt_path))
            self.assertAlmostEqual(pvt.pressure[0], 200 / 0.980665)
            self.assertAlmostEqual(pvt.co[0], 0.001 * 0.980665)
            self.assertAlmostEqual(pvt.Rs[0], 90)

            production_path = root / 'production.csv'
            production_path.write_text(
                'time,Np,Gp,Wp,pressure\n'
                '# days,# m3,# m3,# m3,# kgf/cm2\n'
                '0,0,0,0,200\n'
                '1,100,20000,0,180\n'
                '2,200,40000,0,160\n',
                encoding='utf-8',
            )
            reservoir, production, stoiip_values, statistics = calculate_oil_material_balance(
                str(pvt_path), str(production_path), UnitSystem.METRIC, 200, 82, 0.0,
                cw=4e-5, cf=2e-5, swi=0.3,
            )

            self.assertEqual(len(stoiip_values), 3)
            self.assertEqual(statistics['count'], 2)
            self.assertAlmostEqual(production.pressure[0], 200)
            self.assertIsNotNone(reservoir.F_values[1])
            self.assertNotEqual(reservoir.Eg_values[1], 0)
            self.assertEqual((reservoir.cw, reservoir.cf, reservoir.swi), (4e-5, 2e-5, 0.3))

    def test_reads_semicolon_delimited_pvt_and_production_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pvt_path = root / 'pvt.csv'
            pvt_path.write_text(
                'pressure;Bo;Rs;Bg\n'
                '200;1.2;90;0.005\n'
                '180;1.22;80;0.0055\n',
                encoding='utf-8',
            )
            production_path = root / 'production.csv'
            production_path.write_text(
                'time;Np;Gp;Wp;pressure\n'
                '0;0;0;0;200\n'
                '1;100;20000;0;180\n',
                encoding='utf-8',
            )

            pvt = InputReader.read_pvt_from_csv(str(pvt_path))
            production = InputReader.read_production_from_csv(str(production_path))

        self.assertEqual(pvt.pressure.tolist(), [200, 180])
        self.assertEqual(production.pressure.tolist(), [200, 180])
        self.assertEqual(production.Np.tolist(), [0, 100])


if __name__ == '__main__':
    unittest.main()