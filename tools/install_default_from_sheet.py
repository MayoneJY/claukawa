"""Install the MIT-safe default character pack from a 4x3 chroma-keyed
sprite sheet.

Pipeline per cell: crop -> green chroma-key to alpha -> autocrop -> save as
src/claukawa/assets/gifs/default/{category}.png.

Cell layout (rows top->bottom, cols left->right) maps to categories:
    row 1 col 1: greeting              -> session_start
    row 1 col 2: writing               -> editing
    row 1 col 3: writing_then_thinking -> thinking
    row 1 col 4: reading_book          -> reading
    row 2 col 1: typing                -> bashing
    row 2 col 2: mousing               -> web
    row 2 col 3: cup_phone             -> subagent
    row 2 col 4: question              -> waiting_input
    row 3 col 1: sleeping              -> idle
    row 3 col 2: recalling             -> compacting
    row 3 col 3: crying                -> (unused, written for completeness)
    row 3 col 4: scene_12              -> mcp

Usage:
    python tools/install_default_from_sheet.py <source-image>
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parents[1] / "src" / "claukawa" / "assets" / "gifs" / "default"

# (category-or-extra-name, row, col)
LAYOUT: list[tuple[str, int, int]] = [
    ("session_start", 0, 0),
    ("editing", 0, 1),
    ("thinking", 0, 2),
    ("reading", 0, 3),
    ("bashing", 1, 0),
    ("web", 1, 1),
    ("subagent", 1, 2),
    ("waiting_input", 1, 3),
    ("idle", 2, 0),
    ("compacting", 2, 1),
    ("_crying", 2, 2),  # leading underscore = saved but not category-mapped
    ("mcp", 2, 3),
]

GREEN_DOMINANCE = 1.25
GREEN_MIN = 80


def chroma_key(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if (
                g >= GREEN_MIN
                and g >= r * GREEN_DOMINANCE
                and g >= b * GREEN_DOMINANCE
            ):
                px[x, y] = (r, g, b, 0)
                continue
            if g > r and g > b:
                excess = g - max(r, b)
                if excess > 20:
                    px[x, y] = (r, max(r, b) + 20, b, a)
    return img


def autocrop_alpha(img: Image.Image, padding: int = 6) -> Image.Image:
    bbox = img.getbbox()
    if bbox is None:
        return img
    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(img.width, right + padding)
    bottom = min(img.height, bottom + padding)
    return img.crop((left, top, right, bottom))


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: install_default_from_sheet.py <source-image>", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    if not src.exists():
        print(f"source not found: {src}", file=sys.stderr)
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(src)
    W, H = sheet.size
    rows, cols = 3, 4
    cw, ch = W // cols, H // rows
    print(f"sheet {W}x{H} -> {cols}x{rows} cells of {cw}x{ch}")

    for name, r, c in LAYOUT:
        if name.startswith("_"):
            # Skip cells we explicitly don't ship.
            continue
        box = (c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)
        cell = sheet.crop(box)
        keyed = chroma_key(cell)
        cropped = autocrop_alpha(keyed)
        out_path = OUT / f"{name}.png"
        cropped.save(out_path, format="PNG", optimize=True)
        print(f"wrote {out_path}  ({cropped.size[0]}x{cropped.size[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
