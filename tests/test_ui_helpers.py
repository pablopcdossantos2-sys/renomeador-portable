"""Testes para pequenos auxiliares de navegação da interface."""
import unittest

from main import _wheel_units


class MouseWheelTests(unittest.TestCase):
    def test_windows_wheel_delta_uses_expected_direction_and_steps(self):
        self.assertEqual(_wheel_units(120), -1)
        self.assertEqual(_wheel_units(-120), 1)
        self.assertEqual(_wheel_units(240), -2)
        self.assertEqual(_wheel_units(-240), 2)

    def test_high_resolution_wheel_delta_never_disappears(self):
        self.assertEqual(_wheel_units(1), -1)
        self.assertEqual(_wheel_units(-1), 1)
        self.assertEqual(_wheel_units(0), 0)


if __name__ == "__main__":
    unittest.main()
