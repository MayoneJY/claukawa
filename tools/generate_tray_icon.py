"""Generate the tray / app icon (placeholder).

    python tools/generate_tray_icon.py

Outputs PNG + ICO. .icns generation requires `iconutil` (macOS only) and is
left to the macOS build pipeline (see build/claukawa-mac.spec instructions).
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUTPUT = Path(__file__).resolve().parents[1] / "src" / "claukawa" / "assets"


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(2, size // 16)
    cx = cy = size // 2

    # gradient circle background
    radius = size // 2 - pad
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bg)
    for i in range(radius, 0, -1):
        t = 1 - i / radius
        r = int(60 + (180 - 60) * t)
        g = int(100 + (210 - 100) * t)
        b = int(220 + (255 - 220) * t)
        bd.ellipse((cx - i, cy - i, cx + i, cy + i), fill=(r, g, b, 255))
    img.alpha_composite(bg)

    # speech tail
    tail = [
        (cx - radius * 0.45, cy + radius * 0.55),
        (cx - radius * 0.05, cy + radius * 0.10),
        (cx - radius * 0.55, cy + radius * 0.25),
    ]
    d.polygon(tail, fill=(255, 255, 255, 230))

    # three dots inside (chat indicator)
    dot_r = max(2, size // 14)
    spacing = size // 5
    for i in (-1, 0, 1):
        x = cx + i * spacing
        y = cy - dot_r // 2
        d.ellipse((x - dot_r, y - dot_r, x + dot_r, y + dot_r), fill=(255, 255, 255, 240))
    return img


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = [make_icon(s) for s in sizes]

    # PNG (largest, used as fallback)
    png_path = OUTPUT / "tray_icon.png"
    images[-1].save(png_path)
    print(f"wrote {png_path}")

    # ICO (multi-resolution)
    ico_path = OUTPUT / "tray_icon.ico"
    images[-1].save(ico_path, sizes=[(s, s) for s in sizes])
    print(f"wrote {ico_path}")

    # Template image for macOS menu bar (monochrome alpha)
    tpl_size = 44
    tpl = Image.new("RGBA", (tpl_size, tpl_size), (0, 0, 0, 0))
    td = ImageDraw.Draw(tpl)
    td.ellipse((2, 2, tpl_size - 3, tpl_size - 3), outline=(0, 0, 0, 255), width=2)
    dot_r = 3
    for i in (-1, 0, 1):
        x = tpl_size // 2 + i * 8
        y = tpl_size // 2
        td.ellipse((x - dot_r, y - dot_r, x + dot_r, y + dot_r), fill=(0, 0, 0, 255))
    tpl_path = OUTPUT / "tray_icon_template.png"
    tpl.save(tpl_path)
    print(f"wrote {tpl_path}")


if __name__ == "__main__":
    main()
