"""Testes independentes de contraste para as paletas da interface."""
import unittest

from theme import PALETTES


def _luminance(color: str) -> float:
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    light, dark = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class PaletteContrastTests(unittest.TestCase):
    def test_muted_text_is_readable_on_table_and_selection_backgrounds(self):
        for name, palette in PALETTES.items():
            with self.subTest(theme=name):
                self.assertGreaterEqual(contrast_ratio(palette["muted"], palette["heading"]), 4.5)
                self.assertGreaterEqual(contrast_ratio(palette["muted"], palette["selection"]), 4.5)

    def test_primary_button_text_is_readable(self):
        foregrounds = {"Escuro": "#0b1220", "Claro": "#ffffff"}
        for name, palette in PALETTES.items():
            with self.subTest(theme=name):
                self.assertGreaterEqual(contrast_ratio(foregrounds[name], palette["blue"]), 4.5)


if __name__ == "__main__":
    unittest.main()
