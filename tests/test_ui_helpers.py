"""Testes para pequenos auxiliares de navegação da interface."""
import unittest

from main import _layout_mode, _wheel_units


class ResponsiveLayoutTests(unittest.TestCase):
    def test_switches_to_compact_layout_below_breakpoint(self):
        self.assertEqual(_layout_mode(1039), "compact")
        self.assertEqual(_layout_mode(760), "compact")

    def test_uses_two_columns_at_or_above_breakpoint(self):
        self.assertEqual(_layout_mode(1040), "wide")
        self.assertEqual(_layout_mode(1240), "wide")


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
