"""Tokens visuais do Renomeador Portátil, sem dependência de Tkinter."""
from __future__ import annotations

SPACE = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}
FONT_UI = "Segoe UI"
FONT_MONO = ("Cascadia Mono", "Consolas", "Courier New")

PALETTES = {
    "Escuro": {
        "app": "#111827",
        "surface": "#1f2937",
        "surface_alt": "#273244",
        "navy": "#1f2937",
        "navy_light": "#374151",
        "ink": "#e5e7eb",
        "muted": "#aab2bf",
        "border": "#374151",
        "blue": "#60a5fa",
        "blue_hover": "#3b82f6",
        "blue_soft": "#263b58",
        "green": "#6ee7b7",
        "green_soft": "#19382f",
        "red": "#fca5a5",
        "red_soft": "#3f2528",
        "amber": "#fcd34d",
        "amber_soft": "#3b3120",
        "row_alt": "#202b3b",
        "log": "#111827",
        "log_text": "#d1d5db",
        "heading": "#374151",
        "input": "#1f2937",
        "selection": "#2d4058",
        "white": "#ffffff",
    },
    "Claro": {
        "app": "#f7f8fa",
        "surface": "#ffffff",
        "surface_alt": "#f3f4f6",
        "navy": "#1f2937",
        "navy_light": "#374151",
        "ink": "#111827",
        "muted": "#5b6472",
        "border": "#e5e7eb",
        "blue": "#2563eb",
        "blue_hover": "#1d4ed8",
        "blue_soft": "#eff6ff",
        "green": "#047857",
        "green_soft": "#ecfdf5",
        "red": "#b91c1c",
        "red_soft": "#fef2f2",
        "amber": "#92400e",
        "amber_soft": "#fffbeb",
        "row_alt": "#f9fafb",
        "log": "#1f2937",
        "log_text": "#e5e7eb",
        "heading": "#f3f4f6",
        "input": "#ffffff",
        "selection": "#e6efff",
        "white": "#ffffff",
    },
}

def frame_background_color(palette: dict[str, str], role: str) -> str:
    """Resolve os papéis visuais da interface para uma cor válida da paleta."""
    palette_key = {"header": "navy", "header_text": "navy", "accent": "blue"}.get(role, role)
    return palette.get(palette_key, palette["app"])
