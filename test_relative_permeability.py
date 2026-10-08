import unittest

import numpy as np

from material_balance.relative_permeability_app import (
    DEFAULTS,
    format_opm_tables,
    generate_corey_curves,
)


def default_parameters():
    parameters = {key: float(value) for key, value in DEFAULTS.items()}
    parameters['points'] = int(parameters['points'])
    return parameters


class RelativePermeabilityTests(unittest.TestCase):
    def test_curves_are_monotonic_and_reach_configured_endpoints(self):
        parameters = default_parameters()
        curves = generate_corey_curves(parameters)

        for increasing in ('krw', 'krg'):
            self.assertTrue(np.all(np.diff(curves[increasing]) >= 0))
        for decreasing in ('krow', 'krog'):
            self.assertTrue(np.all(np.diff(curves[decreasing]) <= 0))

        self.assertAlmostEqual(curves['krw'][0], 0.0)
        self.assertAlmostEqual(curves['krw'][-1], parameters['krw_end'])
        self.assertAlmostEqual(curves['krow'][0], parameters['krow_end'])
        self.assertAlmostEqual(curves['krow'][-1], 0.0)
        self.assertAlmostEqual(curves['krg'][0], 0.0)
        self.assertAlmostEqual(curves['krg'][-1], parameters['krg_end'])
        self.assertAlmostEqual(curves['krog'][0], parameters['krog_end'])
        self.assertAlmostEqual(curves['krog'][-1], 0.0)

    def test_exports_swof_and_sgof_keyword_blocks(self):
        curves = generate_corey_curves(default_parameters())

        output = format_opm_tables(curves)
        self.assertIn('SWOF\n-- SW KRW KROW PCOW', output)
        self.assertIn('SGOF\n-- SG KRG KROG PCGO', output)
        self.assertEqual(output.count('/'), 2)
        self.assertIn('0.00000000 0.00000000 1.00000000 0.0', output)

        self.assertTrue(format_opm_tables(curves, 'SWOF').startswith('SWOF\n'))
        self.assertTrue(format_opm_tables(curves, 'SGOF').startswith('SGOF\n'))

    def test_rejects_overlapping_saturation_endpoints(self):
        parameters = default_parameters()
        parameters['swc'] = 0.8
        parameters['sorw'] = 0.2

        with self.assertRaisesRegex(ValueError, 'must sum to less than 1'):
            generate_corey_curves(parameters)

    def test_rejects_invalid_corey_exponents(self):
        parameters = default_parameters()
        parameters['nw'] = 0

        with self.assertRaisesRegex(ValueError, 'greater than zero'):
            generate_corey_curves(parameters)

    def test_rejects_non_finite_parameters(self):
        parameters = default_parameters()
        parameters['nog'] = float('nan')

        with self.assertRaisesRegex(ValueError, 'finite numbers'):
            generate_corey_curves(parameters)


if __name__ == '__main__':
    unittest.main()