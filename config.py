"""Persistência tolerante das preferências do usuário."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile


def _config_path() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home())
    return base / "RenomeadorPortatil" / "config.json"


def load_config() -> dict:
    """Carrega preferências; qualquer falha retorna um dicionário vazio."""
    try:
        data = json.loads(_config_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def save_config(data: dict) -> None:
    """Grava preferências de forma atômica, sem interromper o aplicativo."""
    path = _config_path()
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix="config.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    except (OSError, TypeError, ValueError):
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def system_theme() -> str:
    """Detecta o tema de aplicativos do Windows; usa Claro como fallback."""
    if os.name != "nt":
        return "Claro"
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            return "Claro" if winreg.QueryValueEx(key, "AppsUseLightTheme")[0] else "Escuro"
    except (OSError, ImportError):
        return "Claro"
