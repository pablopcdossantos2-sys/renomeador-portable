"""Gera PNG e ICO do Renomeador Portátil com Pillow."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets"


def _make_icon(size: int = 512) -> Image.Image:
    scale = size / 512
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(values):
        return tuple(round(value * scale) for value in values)

    # Fundo azul com gradiente suave, recortado em cantos arredondados.
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(box((14, 14, 498, 498)), radius=round(112 * scale), fill=255)
    pixels = image.load()
    for y in range(size):
        ratio = y / max(1, size - 1)
        top = (55, 163, 255)
        bottom = (7, 75, 198)
        color = tuple(round(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3)) + (255,)
        for x in range(size):
            if mask.getpixel((x, y)):
                pixels[x, y] = color

    draw = ImageDraw.Draw(image)
    white = (255, 255, 255, 255)
    folder = (230, 243, 255, 255)
    blue = (18, 91, 196, 255)

    # Pasta com aba em estilo geométrico.
    folder_points = [
        (91, 172), (91, 163), (97, 151), (110, 148), (216, 148),
        (252, 184), (395, 184), (411, 190), (418, 205), (418, 351),
        (413, 368), (398, 377), (110, 377), (96, 371), (91, 358),
    ]
    draw.polygon([tuple(round(v * scale) for v in point) for point in folder_points], fill=folder)
    draw.line([tuple(round(v * scale) for v in point) for point in folder_points + [folder_points[0]]],
              fill=white, width=max(2, round(7 * scale)), joint="curve")

    # Duas setas circulares simbolizando a renomeação/atualização.
    draw.arc(box((153, 199, 350, 361)), start=201, end=345, fill=blue, width=max(3, round(22 * scale)))
    draw.polygon(
        [tuple(round(v * scale) for v in point) for point in [(318, 197), (353, 214), (321, 235)]],
        fill=blue,
    )
    draw.arc(box((163, 207, 359, 370)), start=22, end=166, fill=blue, width=max(3, round(22 * scale)))
    draw.polygon(
        [tuple(round(v * scale) for v in point) for point in [(195, 365), (160, 347), (192, 327)]],
        fill=blue,
    )
    return image


def ensure_icon_assets() -> tuple[Path, Path]:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    base = _make_icon(512)
    png_path = ASSET_DIR / "renomeador.png"
    ico_path = ASSET_DIR / "renomeador.ico"
    # A imagem PNG é usada pelo Tkinter na barra de título; mantenha-a pequena.
    base.resize((64, 64), Image.Resampling.LANCZOS).save(png_path, format="PNG", optimize=True)
    # O ICO contém vários tamanhos para Explorador, barra de tarefas e atalhos.
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base.save(ico_path, format="ICO", sizes=[(size, size) for size in sizes])
    return png_path, ico_path


if __name__ == "__main__":
    png, ico = ensure_icon_assets()
    print(f"Ícone PNG criado: {png}")
    print(f"Ícone ICO criado: {ico}")
