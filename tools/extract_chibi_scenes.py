"""Cut a 4x3 chibi sprite-sheet, chroma-key the green background to alpha,
and save individual transparent PNGs into the assets folder.

Usage:
    python tools/extract_chibi_scenes.py <source-image>

Layout (rows top->bottom, cols left->right):
    row 1 col 1: 인사 (greeting)
    row 1 col 2: 글쓰기 (writing)
    row 1 col 3: 글쓰다 생각 (writing_then_thinking)
    row 1 col 4: 책 읽기 (reading_book)
    row 2 col 1: 노트북 타자 (typing)
    row 2 col 2: 마우스 움직이기 (mousing)
    row 2 col 3: 종이컵 전화 (cup_phone)
    row 2 col 4: ? (question)
    row 3 col 1: 엎드려 자기 (sleeping)
    row 3 col 2: 고개 기울여 회상 (recalling)
    row 3 col 3: 우는 (crying)
    row 3 col 4: (extra; saved as scene_12)
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

OUT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "claukawa"
    / "assets"
    / "scenes"
    / "chibi"
)

NAMES = [
    ["greeting", "writing", "writing_then_thinking", "reading_book"],
    ["typing", "mousing", "cup_phone", "question"],
    ["sleeping", "recalling", "crying", "scene_12"],
]

# Chroma-key thresholds. The reference green is ~ (60, 200, 40)-ish; tune if
# needed by re-running with different values.
GREEN_DOMINANCE = 1.25  # green channel must exceed both R and B by this factor
GREEN_MIN = 80          # absolute minimum on green channel to be considered "green"
EDGE_FEATHER = 1        # how aggressively we expand alpha=0 into near-green pixels


def chroma_key(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if (
                g >= GREEN_MIN
                and g >= r * GREEN_DOMINANCE
                and g >= b * GREEN_DOMINANCE
            ):
                pixels[x, y] = (r, g, b, 0)
                continue
            # Mild despill: if green is still dominant but not enough for full
            # transparency, dampen the green channel to remove green halos on
            # the figure edges.
            if g > r and g > b:
                excess = g - max(r, b)
                if excess > 20:
                    g_new = max(r, b) + 20
                    pixels[x, y] = (r, g_new, b, a)
    return img


ROW_TOP_TRIM = (0, 0, 5)  # extra pixels shaved off the top of each row


def crop_grid(img: Image.Image, rows: int, cols: int) -> list[list[Image.Image]]:
    w, h = img.size
    cw, ch = w // cols, h // rows
    out: list[list[Image.Image]] = []
    for r in range(rows):
        trim = ROW_TOP_TRIM[r] if r < len(ROW_TOP_TRIM) else 0
        row: list[Image.Image] = []
        for c in range(cols):
            box = (c * cw, r * ch + trim, (c + 1) * cw, (r + 1) * ch)
            row.append(img.crop(box))
        out.append(row)
    return out


def autocrop_alpha(img: Image.Image, padding: int = 6) -> Image.Image:
    """Tighten the bbox to the non-transparent content, with small padding."""
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
        print("usage: extract_chibi_scenes.py <source-image>", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    if not src.exists():
        print(f"source not found: {src}", file=sys.stderr)
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    img = Image.open(src)
    grid = crop_grid(img, rows=3, cols=4)
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            keyed = chroma_key(cell)
            keyed = autocrop_alpha(keyed)
            name = NAMES[r][c]
            out_path = OUT / f"{name}.png"
            keyed.save(out_path)
            print(f"wrote {out_path}  ({keyed.size[0]}x{keyed.size[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
