"""Convert a chroma-keyed sprite sheet (rows × cols of equal cells) into a
seamless animated GIF with transparent background.

Usage:
    python tools/spritesheet_to_gif.py <source-png> <output-gif> [rows] [cols] [duration_ms]

Defaults: rows=5 cols=6 duration_ms=80
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

GREEN_DOMINANCE = 1.15
GREEN_MIN = 60
EDGE_TRIM = 3  # px shaved off every cell edge before chroma-key (eats divider lines)


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


def align_bottoms(frames: list[Image.Image]) -> list[Image.Image]:
    """Shift each frame vertically so its content bottom shares the same Y.

    Removes the cumulative vertical drift that diffusion models tend to leave
    in sprite-sheet loops. Anchors on the character's lowest opaque pixel,
    which for a desk-sitting character is the desk's bottom edge.
    """
    bottoms: list[int] = []
    for f in frames:
        bb = f.getbbox()
        bottoms.append(bb[3] if bb else 0)
    if not bottoms:
        return frames
    target = max(bottoms)  # deepest bottom across the loop
    out: list[Image.Image] = []
    for f, b in zip(frames, bottoms):
        if b == 0 or b == target:
            out.append(f)
            continue
        canvas = Image.new("RGBA", f.size, (0, 0, 0, 0))
        canvas.paste(f, (0, target - b))
        out.append(canvas)
    return out


def union_bbox(frames: list[Image.Image]) -> tuple[int, int, int, int] | None:
    box: list[int] | None = None
    for f in frames:
        bb = f.getbbox()
        if bb is None:
            continue
        if box is None:
            box = list(bb)
        else:
            box[0] = min(box[0], bb[0])
            box[1] = min(box[1], bb[1])
            box[2] = max(box[2], bb[2])
            box[3] = max(box[3], bb[3])
    return tuple(box) if box else None


def to_paletted(frame_rgba: Image.Image) -> Image.Image:
    """Convert RGBA -> P with transparent index 255, preserving alpha < 128
    as transparent and quantizing the remaining colors."""
    alpha = frame_rgba.split()[-1]
    rgb = frame_rgba.convert("RGB")
    p = rgb.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    mask = alpha.point(lambda a: 255 if a < 128 else 0)
    p.paste(255, mask=mask)
    p.info["transparency"] = 255
    return p


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    rows = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    cols = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    duration = int(sys.argv[5]) if len(sys.argv) > 5 else 80

    if not src.exists():
        print(f"missing source: {src}", file=sys.stderr)
        return 2

    sheet = Image.open(src).convert("RGBA")
    W, H = sheet.size
    cw, ch = W // cols, H // rows
    print(f"sheet {W}x{H} -> {cols}x{rows} cells, each {cw}x{ch}")

    # cut + chroma key in reading order. Shave EDGE_TRIM px off each cell first
    # to discard any divider line / cell-boundary green leak the model painted.
    frames_rgba: list[Image.Image] = []
    for r in range(rows):
        for c in range(cols):
            box = (
                c * cw + EDGE_TRIM,
                r * ch + EDGE_TRIM,
                (c + 1) * cw - EDGE_TRIM,
                (r + 1) * ch - EDGE_TRIM,
            )
            cell = sheet.crop(box)
            frames_rgba.append(chroma_key(cell))
    cw_eff = cw - 2 * EDGE_TRIM
    ch_eff = ch - 2 * EDGE_TRIM

    # Bottom-anchor each frame so cumulative vertical drift across the loop
    # is removed. The character's lowest opaque pixel maps to the same Y in
    # every frame; head/limb motion above stays intact.
    frames_rgba = align_bottoms(frames_rgba)

    # find common bbox so all frames share consistent dimensions and the motion
    # plays without jitter
    bb = union_bbox(frames_rgba)
    if bb is None:
        print("all frames empty after chroma-key — bailing", file=sys.stderr)
        return 1
    pad = 8
    left = max(0, bb[0] - pad)
    top = max(0, bb[1] - pad)
    right = min(cw_eff, bb[2] + pad)
    bottom = min(ch_eff, bb[3] + pad)
    print(f"union bbox (padded): ({left},{top},{right},{bottom})")
    frames_rgba = [f.crop((left, top, right, bottom)) for f in frames_rgba]

    paletted = [to_paletted(f) for f in frames_rgba]

    dst.parent.mkdir(parents=True, exist_ok=True)
    paletted[0].save(
        dst,
        format="GIF",
        save_all=True,
        append_images=paletted[1:],
        duration=duration,
        loop=0,
        disposal=2,
        transparency=255,
        optimize=False,
    )
    print(f"wrote {dst}  ({len(paletted)} frames @ {duration}ms)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
