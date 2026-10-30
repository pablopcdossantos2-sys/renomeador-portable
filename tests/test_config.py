"""Testes da persistência de preferências, sem depender do perfil real do usuário."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config


class ConfigTests(unittest.TestCase):
    def test_save_and_load_preferences(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "config.json"
            with patch("config._config_path", return_value=target):
                config.save_config({"theme": "Escuro", "last_folder": "C:/Dados", "recursive": False})
                self.assertEqual(
                    config.load_config(),
                    {"theme": "Escuro", "last_folder": "C:/Dados", "recursive": False},
                )

    def test_invalid_config_returns_empty_preferences(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "config.json"
            target.write_text("{ inválido", encoding="utf-8")
            with patch("config._config_path", return_value=target):
                self.assertEqual(config.load_config(), {})

    def test_non_dictionary_config_returns_empty_preferences(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "config.json"
            target.write_text("[]", encoding="utf-8")
            with patch("config._config_path", return_value=target):
                self.assertEqual(config.load_config(), {})


if __name__ == "__main__":
    unittest.main()
