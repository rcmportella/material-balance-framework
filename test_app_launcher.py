import sys
import unittest
from pathlib import Path

from Petroleum_Engineering_Apps import get_applications


class ApplicationLauncherTests(unittest.TestCase):
    def test_catalog_contains_all_desktop_applications(self):
        applications = get_applications(Path(__file__).resolve().parent)

        self.assertEqual(
            [application.name for application in applications],
            [
                'Oil Material Balance',
                'Gas P/Z Analysis',
                'PVT Table Generator',
                'Relative Permeability (Corey)',
                'Production Decline',
                'Well Production Viewer',
            ],
        )
        self.assertTrue(all(application.command[0] == sys.executable for application in applications))

    def test_example_application_scripts_exist(self):
        applications = get_applications(Path(__file__).resolve().parent)
        example_commands = [
            application.command[-1]
            for application in applications
            if application.category == 'Well Production'
        ]

        self.assertEqual(len(example_commands), 2)
        self.assertTrue(all(Path(command).is_file() for command in example_commands))


if __name__ == '__main__':
    unittest.main()